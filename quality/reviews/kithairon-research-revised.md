# Kithairon 外部盲评意见修订版

日期：2026-05-19

本稿基于 `/Users/chenmohan/Downloads/kithairon-research.md` 的外部 LLM 盲评意见，并按当前仓库事实重新校准。校准依据包括 README、`docs/`、核心 Python 源码、API 路由、测试目录、GitHub Actions 配置、仓库元数据，以及对 read-only render 行为的定向复现。

本稿不是一次完整 CI 复跑或音乐审美验收；它更适合作为 release readiness 和后续重构 backlog 的整理版本。

## 修订评分

参考评分：**82 / 100**

这个分数可以保留，但解释需要调整：Kithairon 的工程化程度比原盲评中部分表述更强，尤其是当前 CI 已经覆盖 Python lint/type/test、前端 lint/test/e2e/build 和 Cremona refactor audit；同时，read-only render 确认为真实 mutation bug，会抵消一部分工程成熟度得分。

| 维度 | 分数 | 修订后评价 |
| --- | ---: | --- |
| 项目定位与完整度 | 17 / 20 | 项目目标清晰：从单声部旋律生成 strict / relaxed canon，并输出 MIDI、MusicXML、JSON、Markdown report、resolved config 和可视化工件。README 能支撑工程用户上手，但首页缺少更直观的音乐演示。 |
| 技术实现 | 24 / 30 | IR、transform、rules、scoring、repair beam search、CP-SAT solver、导出和 visualization artifact 形成了完整管线。扣分点主要是 solver objective 仍偏启发式，以及 read-only render 写入问题已经被确认。 |
| 工程化 | 19 / 20 | Python 3.12、`uv`、Ruff、Pyright、pytest、coverage、Cremona 和 GitHub Actions 已经接入；CI 也已使用 `pnpm/action-setup@v6`、Node 24 和 Playwright E2E。 |
| 测试质量 | 13 / 15 | 单元、集成、golden snapshot、property-based tests 和 visualization examples 覆盖了关键路径。仍缺少 read-only render 回归测试，以及面向真实旋律样本的 benchmark 夹具。 |
| 文档与可用性 | 5 / 8 | README、development docs 和 visualization docs 已能解释基本使用和部署，但缺少 scoring/rules 的音乐假设说明、架构图、FAQ、适合/不适合旋律类型，以及首页 demo。README 的输出文件清单也需要补充 `visualization.json` 和 `artifact_index.json`。 |
| 产品化/开源成熟度 | 4 / 7 | 仓库是公开仓库，但 GitHub description、topics、release 仍为空；缺少 CHANGELOG、contribution guide 和可快速建立信任的 demo asset。 |

## 可接受结论

这份外部盲评可以被项目接受为一份有效的 backlog/release-readiness 审计，但不应作为完全权威的质量判定。它没有实际安装依赖、运行完整测试或试听输出，因此对音乐质量和运行可靠性的判断只能算静态推断。

应当直接接受的部分：

- README 和项目首页缺少“30 秒 demo”。
- scoring/rules 的音乐假设需要集中公开说明。
- read-only render endpoint 会写入 artifact，和 read-only 语义冲突。
- 缺少真实旋律 benchmark 集合。
- 开源发布包装不足，包括 release、CHANGELOG、description、topics 和贡献说明。

需要降级或重新表述的部分：

- “CI 是否完善”的担忧应降级。当前 CI 已经包含 `ruff`、`pyright`、`pytest`、前端 lint/test/e2e/build 和 Cremona audit。
- “solver objective 需要模块化/可配置化”是合理中期重构，但不应作为当前发布前阻塞项。更稳妥的顺序是先补文档、benchmark 和回归测试，再决定 objective 抽象边界。
- “产品化/开源成熟度”不应和核心代码质量混为一谈。它影响外部采用和信任，但不是当前生成管线正确性的直接证据。

## 已确认的问题

### 1. read-only render 语义不完整

`src/kithairon/api/routes_artifacts.py` 中的 render candidate 路径会调用 MuseScore 渲染文件，并随后更新 `artifact_index.json`。当前入口只检查 `settings.musescore_bin`，没有检查 `settings.read_only`。

定向复现结果：

- 使用正常 app 创建 run。
- 用同一个 output root 启动 `read_only=True` app。
- 配置假的 MuseScore 可执行文件调用 render endpoint。
- endpoint 返回 `200`，并实际写出 `renders/...pdf`。

这说明原盲评中的“read-only 语义疑似不完整”应从疑似升级为确认 bug。建议优先修复，并新增集成测试，期望 read-only render 返回 `read_only_mode` 错误且不写入任何 render artifact。

### 2. README demo 与输出清单不足

当前 README 能解释安装、quickstart、engine examples、strict/relaxed canon、input formats、config、errors 和 development gate。但它还缺少面向首次访问者的直观演示：

- 一段输入旋律。
- 生成后的谱例截图。
- MIDI 或音频 demo。
- Web visualization 截图或短 gif。

此外，README quickstart 的 output directory 清单列出了 `results.json`、`report.md`、`resolved_config.toml`、`candidates/*.musicxml` 和 `candidates/*.mid`，但当前 pipeline 还会生成 `visualization.json` 与 `artifact_index.json`。这部分应同步更新。

### 3. scoring/rules 文档缺位

项目代码已经表达了清晰的音乐假设，例如：

- 协和音程集合。
- strict / relaxed canon 的区分。
- strong beat、parallel perfect、cadence 等规则或 penalty。
- `permissive`、`pop-lite`、`renaissance-lite` 等 profile。

但这些假设目前主要散落在代码和测试中。外部用户无法快速理解：

- 哪些是硬约束，哪些是软偏好。
- 权重如何影响候选排序。
- 每个 score profile 面向什么风格。
- 哪些旋律类型容易失败。
- relaxed canon 为什么仍然被视为 canon 变体。

建议新增一篇 `docs/scoring-and-rules.md`，并从 README 链接过去。

### 4. 真实旋律 benchmark 不足

`examples/melodies/` 已经有基础示例和 `bad_for_canon`，测试也会跑 visualization examples。但它还不像 benchmark suite，缺少一组能稳定代表产品边界的真实旋律样本。

建议补充：

- folk melody。
- children song。
- stepwise diatonic melody。
- chromatic melody。
- rhythmically sparse melody。
- bad-for-canon negative example。

每个样本最好记录预期引擎、典型输出、人工备注和已知失败模式。这个集合不一定一开始就作为硬性 golden truth，但可以作为 solver/scoring 调整时的回归观察集。

### 5. 开源发布信息不足

当前 GitHub 仓库元数据仍然偏空：

- description 为空。
- topics 为空。
- latest release 为空。
- stars/forks 均为 0。

stars/forks 不应被当作质量问题，但 description、topics、release、CHANGELOG 和贡献说明是项目对外发布的基础包装。建议在 v0.1.0 前补齐。

## 建议优先级

P0：

- 修复 read-only render mutation bug。
- 新增 read-only render 回归测试，确认不会写入 render output 或更新 artifact index。

P1：

- 更新 README quickstart 的 output directory 清单，补充 `visualization.json` 和 `artifact_index.json`。
- 在 README 顶部加入 30 秒 demo：输入、输出谱例、MIDI/audio 或短 gif。
- 新增 `docs/scoring-and-rules.md`，解释 scoring philosophy、硬/软规则、profile 和失败模式。

P2：

- 建立真实旋律 benchmark/examples 集合。
- 补 GitHub description、topics、CHANGELOG、contribution guide。
- 发布 `v0.1.0` release。

P3：

- 在 benchmark 和文档稳定后，再考虑 solver objective 的模块化与配置化。
- 将 solver objective 的常量、cadence preference、pitch option search 和 edit weighting 拆成更清晰的测试单元。

## 修订后的五条核心建议

1. **先修 API read-only 语义。** 这是确认存在的行为 bug，不只是文档或产品包装问题。
2. **把 README 调整成能快速展示成果的首页。** 当前 README 面向工程运行已经够用，但缺少音乐结果的第一印象。
3. **补 scoring/rules 文档。** 让用户知道 Kithairon 的规则偏好、适用风格和 relaxed canon 边界。
4. **用真实旋律样本约束后续重构。** 在调整 solver/scoring 前，先建立可重复观察的 benchmark。
5. **把开源发布包装补齐。** description、topics、CHANGELOG、release 和 contribution guide 能显著降低外部试用门槛。

## 最终判断

原盲评的主方向可以接受，但应按当前仓库事实重写。Kithairon 当前不是“缺少基础工程保障”的项目；它的问题更集中在一个确认的 API mutation bug、文档解释力、demo 展示、真实样本验证和 release packaging 上。

因此，本项目应接受这份盲评的改进方向，但按上述优先级落地，而不是把所有建议都视作同等紧急的发布阻塞项。
