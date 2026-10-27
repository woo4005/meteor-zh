## 变更说明

<!-- 这个 PR 做了什么、为什么做。翻译类 PR 请写清新增/修正了哪些条目。 -->

## 关联 issue

<!-- 用 Closes / Fixes 关联，例如：Closes #123。没有对应 issue 可写「无」并说明动机。 -->

Closes #

## 变更类型

- [ ] 翻译（词典 / 术语）
- [ ] 修复（Bug）
- [ ] 功能（新特性）
- [ ] 文档（README / CONTRIBUTING / 模板）
- [ ] 构建 / 工程（脚本、打包）

## 检查清单

- [ ] 已运行 `python scripts/build_dict.py`，`src/main/resources/assets/meteorzh/lang/zh.json` 已重新生成并提交
- [ ] 已运行 `python scripts/verify_dict.py`，无异常
- [ ] 新增 / 修改的词典键与英文原串**逐字符一致**（含尾部空格与冒号）
- [ ] 没有改动 `SettingGroup.name`（也没有其它破坏存档序列化的改动）
- [ ] Java 源码符合 **mojmap** 命名（不是 yarn），例如 `SharedSuggestionProvider` / `Component`
- [ ] 版本号处理正确：普通 PR 不动版本号；发版 PR 改了 `gradle.properties` 的 `mod_version`（唯一版本源，`fabric.mod.json` 用 `${version}` 占位），离线发布同时对齐 `scripts/build.py` 的 `VERSION`
- [ ] 相关文档已更新（README「已知边界」/ CONTRIBUTING / Issue 模板）
- [ ] 提交中不含 `build/` 等编译中间产物，`dist/` 只提交发版 jar
- [ ] 已实际验证：`gradlew.bat build`（或 `python scripts/build.py`）通过，必要时进游戏点过界面

## 截图 / 验证记录（可选）

<!-- 翻译改动前后对比、游戏内截图、脚本输出条数变化等。 -->
