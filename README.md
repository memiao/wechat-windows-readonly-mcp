# WeChat Windows 只读接入 MCP（微信 4.1.x / Windows 11）

把 **Windows 版微信 4.x** 的本地聊天记录，以**只读**方式接入任何支持 MCP 的 AI 助手（OpenMausBot / Claude / Cursor 等）。数据不出本机，不替你发消息，不需要 Hook / 注入微信进程。

> 本方案是在 macOS 开源项目 [willwill85/Wechat-MCP](https://github.com/willwill85/Wechat-MCP)（B 站视频 BV1SbsE6aEWt 配套）思路上的 **Windows 移植与组合**，已在 **微信 4.1.15.56 / Windows 11** 实测通过（23/24 数据库解密成功）。

## 架构

```
┌─────────────────────────────────────────────────┐
│  AI 助手（MCP 客户端）                            │
│   └─ stdio ── wxq-mcp（8 个只读工具）             │
│        └─ 读取 ~/.wxq/all_keys.json + 微信 db     │
│              ▲                                   │
│  密钥来源：wechat4-db-decrypt                     │
│   （只读扫描 Weixin.exe 内存中的 Config.Cipher）   │
└─────────────────────────────────────────────────┘
```

| 组件 | 作用 | 来源 |
|---|---|---|
| [fangtimmy/wechat4-db-decrypt](https://github.com/fangtimmy/wechat4-db-decrypt) | 从运行中的微信进程**只读**提取数据库密钥（支持 4.1.11–4.1.15 的 Config.Cipher 内存扫描） | 现成 |
| [vpcoderli/wxq](https://github.com/vpcoderli/wxq) | 用密钥解密并查询聊天记录；自带 `wxq-mcp` stdio MCP 服务 | 现成 |
| 本项目 | 两者的桥接：把 wechat4-db-decrypt 的密钥格式转换为 wxq 格式 + 完整配置说明 | 本仓库 |

> ⚠️ wxq 自带的密钥扫描只支持微信 4.0–4.1.9（`x'<hex>'` 字符串模式）。**4.1.10 起该字符串不再驻留内存**，所以必须用 wechat4-db-decrypt 的 Config.Cipher 扫描代替——这正是本项目的价值。

## 前提

- Windows 10/11，微信 **4.1.11+**（实测 4.1.15.56），**保持登录运行**
- Python 3.10+
- 只读：本方案**不修改、不注入**微信，只读其进程内存与数据库文件

## 安装步骤

### 1. 安装两个工具

```bash
pip install git+https://github.com/fangtimmy/wechat4-db-decrypt.git
pip install "wxq[mcp] @ git+https://github.com/vpcoderli/wxq.git"
```

（也可 clone 后 `pip install -e .`）

### 2. 提取数据库密钥

确保微信已登录运行，然后：

```bash
python -I -m wxexport.keys.hunt
```

- 扫描 Weixin.exe 进程内存中的 `Config.Cipher` 对象，对 `db_storage` 下每个 `.db` 逐一验证（HMAC-SHA512 + PBKDF2）
- 成功后写出 `all_keys.json`（**这是敏感文件，见下方安全说明**）
- 输出示例：`结果: 23/24 salts 找到密钥`（个别迁移残留库如 `migrate/unspportmsg.db` 失败属正常）

### 3. 转换密钥格式给 wxq

wechat4-db-decrypt 的输出带一个 `_meta` 条目，wxq 不需要。运行本仓库的脚本（或手动删掉 `_meta` 条目）：

```bash
python convert_keys.py all_keys.json
```

### 4. 配置 wxq

创建 `~/.wxq/config.json`：

```json
{
  "db_dir": "<你的微信 db_storage 目录>",
  "keys_file": "C:\\Users\\<你>\\.wxq\\all_keys.json"
}
```

`db_dir` 形如 `D:\...\xwechat_files\wxid_xxxx\db_storage`（密钥提取输出里会给出）。

### 5. 验证

```bash
# Windows GBK 终端先设 UTF-8，否则中文/emoji 输出会报 UnicodeEncodeError
set PYTHONIOENCODING=utf-8 && set PYTHONUTF8=1
wxq sessions
```

能看到真实会话列表和未读数即成功。

### 6. 接入 MCP 客户端

`wxq-mcp` 是 stdio MCP 服务。以 OpenMausBot / Claude Desktop 类配置为例：

```json
{
  "mcpServers": {
    "wxq": {
      "command": "cmd",
      "args": ["/c", "wxq-mcp"],
      "env": { "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1" }
    }
  }
}
```

就绪后获得 8 个只读工具：`get_sessions`、`get_unread`、`get_contacts`、`get_contact_detail`、`get_chat_history`、`search_messages`、`get_chat_stats`、`get_group_members`。

## 安全边界

- ✅ **只读**：只扫描内存、只读数据库文件，不修改微信、不注入、不 Hook
- ✅ **数据不出本机**：密钥和聊天记录只存在你自己的电脑上；MCP 走 stdio 管道，**不监听任何网络端口**
- ✅ **不代发消息**：没有任何写/发工具
- ⚠️ `all_keys.json` 是你微信数据库的**主密钥**，等同聊天记录本身：不要提交到 git、不要发给任何人、不要放同步盘。本仓库 `.gitignore` 已忽略它

## 已知限制

- 微信必须**登录运行**才能读到新消息（密钥在内存里，重启微信后需重新提取）
- 微信大版本更新可能让内存扫描失效（所有同类方案的通病），需等 wechat4-db-decrypt 社区适配
- 终端编码：Windows GBK 终端需 `PYTHONUTF8=1`，否则含 emoji 的输出会炸

## 致谢

- [willwill85/Wechat-MCP](https://github.com/willwill85/Wechat-MCP) — 原始 macOS 方案与灵感来源
- [fangtimmy/wechat4-db-decrypt](https://github.com/fangtimmy/wechat4-db-decrypt) — Windows 密钥提取（Config.Cipher 扫描）
- [vpcoderli/wxq](https://github.com/vpcoderli/wxq) — 查询引擎与 MCP 服务

## License

MIT（桥接代码与文档部分；两个依赖库各自遵循其原始 License）
