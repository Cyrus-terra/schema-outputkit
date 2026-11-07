# schema-outputkit

[English](README.md) | 简体中文

面向 AI 编程助手的大模型输出开发规范。通过一份可独立使用的 Skill，指导助手复用项目的 SDK 和校验器，让不同模型的业务输出遵守同一份契约。

**安装在编程客户端中，无需安装到模型服务端，也无需作为业务项目的依赖引入。** 应用代码需要实际实现运行时校验和失败恢复。安装插件不会自动改写已有集成，也不能保证任意模型都能满足任意 Schema。

## 指导哪些开发行为

- 每个业务操作使用同一份权威 Schema，切换模型时保持字段、类型、必填/可选/null 语义和序列化规则一致。
- 根据已验证的服务商、模型、接口和 SDK 能力适配请求。
- 在保存数据、执行工具或返回成功前完成结构与业务校验。
- 修复状态按请求隔离，限制总调用次数、整体期限、用量核算和解析资源。
- 明确处理拒答、截断和失败，避免记录原始提示词与完整响应。
- 根据用途保留文本、流式和工具调用契约，普通聊天不强制包装成 JSON。

例如，可以要求助手：“使用项目现有 SDK 和校验器实现发票提取，切换服务商时保持业务 Schema 不变。”助手应先检查消费方，复用或定义 Schema，选择支持的输出模式，校验最终结果并验证相关失败场景。结构一致不代表内容一致或事实正确。

完整规范在 [SKILL.md](skills/schema-outputkit/SKILL.md)。规范、提醒提示词、元数据、注释及维护文档统一使用英文；中文触发词和多语言测试样例属于刻意保留的功能数据。助手仍可按用户偏好的语言回答。

## 快速使用

在检查过的本地副本上，选择一个客户端启动单次会话：

```sh
codebuddy --plugin-dir "/absolute/path/to/schema-outputkit"
claude --plugin-dir "/absolute/path/to/schema-outputkit"
```

需要时手动调用 `/schema-outputkit:schema-outputkit`。自动提醒采用启发式识别，漏掉相关任务时可以显式加载 Skill。

需要持久使用时，在 Claude Code 或 CodeBuddy 内执行：

```text
/plugin marketplace add /absolute/path/to/schema-outputkit
/plugin install schema-outputkit@schema-outputkit --scope user
```

用户级安装后，该客户端开发不同项目时均可使用；团队有意共享配置时可选择项目级。避免同时安装独立 Skill 副本。仓库本身不会修改全局配置。

## 客户端适配

| 客户端 | 安装包装 | 额外提醒 |
| --- | --- | --- |
| Claude Code | 原生插件及本地市场 | 会话启动、相关开发请求、可识别的 Write/Edit 修改 |
| CodeBuddy | 原生插件及本地市场 | 会话启动、相关开发请求、可识别的 Write/Edit 修改 |
| Codex | 插件及本地市场描述 | 无；通过 Skill 发现或调用 |
| Gemini CLI | 原生扩展 | 会话启动 |
| Hermes Agent | Skill 注册适配 | 主 Agent 的首轮调用 |
| OpenClaw | 原生插件及无依赖 ESM 入口 | 无；通过 Skill 发现或调用 |

激活行为受客户端版本与权限影响。多客户端包装不负责调度多个 Agent；委派实现工作时，主 Agent 需要通过宿主机制传递业务契约和适用规范，不能假设子 Agent 自动继承提醒。

六种客户端的安装、独立 Skill、更新、卸载及验证证据见英文 [安装说明](docs/installation.md)。命令提醒需要 Python 3.9+ 和 `python3` 命令，OpenClaw 宿主需要 Node。独立 Skill 不需要插件的 Python 脚本，也不要求业务项目新增依赖。尚未验证原生 Windows Shell 启动。

## 本地检查

```sh
python3 -B scripts/validate_repository.py
python3 -B scripts/validate_repository.py skills/schema-outputkit
python3 -B -m unittest discover -s tests -v
codebuddy plugin validate .codebuddy-plugin/plugin.json
claude plugin validate .claude-plugin/plugin.json
```

包装测试、原生校验、实际客户端发现和真实模型任务是四种不同证据。参见 [验证矩阵](docs/installation.md#verification-evidence)。Hook 测试通过不能证明服务商兼容性或生成代码必然遵守规范。

## 边界与发布

Hooks 只读取有上限的事件输入，输出固定提醒和 Skill 路径；不读取业务文件、不存储事件、不调用模型、不阻断请求、不替换工具输出。请求和代码识别是启发式规则，不能覆盖所有语言语法。修改适配器或准备发布时，请参阅英文 [维护说明](docs/development.md)。

当前仓库包含本地市场描述，不声称已进入官方市场、已发布 npm 包或 GitHub Release。确定 GitHub 位置后再补充真实仓库地址。本地检查无需凭据。

## 许可与参考

使用 [MIT 许可](LICENSE)。客户端包装和提醒模式参考 supercoding，已保留其版权声明。Schema 校验与有限恢复设计借鉴 Instructor，但不包含也不强制依赖 Instructor 运行库。分发插件或独立 Skill 时须保留适用的许可声明。
