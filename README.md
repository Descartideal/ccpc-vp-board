# CCPC VP 榜单生成器

用 RankLand 榜单制作一个可发给队友的单文件 HTML。生成后的页面直接读取查看者的电脑时间，无需运行服务、网络或依赖包。

## 使用

1. 安装 Python 3.10 或更新版本。
2. 双击 `启动.bat`，或在本目录运行 `python server.py`。
3. 在打开的页面粘贴 `https://rl.algoux.cn/ranklist/比赛ID`，或 `https://rl.algoux.cn/collection/official?rankId=比赛ID`；也可选择本地 `.srk.json` 文件。
4. 选择 VP 开始时间并生成。HTML 保存在 `output` 文件夹，也可在页面点击下载。
5. 只把这个 HTML 发给队友即可；他们双击后会自动按各自电脑的当前时间显示。

## 榜单规则

- 仅统计正式队伍，某题通过数达到 **51 队**或正式队伍总数的 **20%（向上取整）**时，显示这道题的整列数据；两者先到者生效。
- 使用 SRK 的相对比赛时间重放队伍提交。若有 `solutions`，使用逐次提交记录；否则使用 `result/time/tries` 摘要。
- VP 开始 4 小时后，所有题目显示，成绩固定在原比赛前 4 小时。排名按显示题目的通过数和罚时计算，非正式队伍以 `*` 标记。
- 时间由设备本地时钟决定；HTML 内含完整原始榜单，适合队友互信的 VP，不适合防作弊比赛。

来源：[RankLand](https://rl.algoux.cn/) 与 [Standard Ranklist 规范](https://github.com/algoux/standard-ranklist/tree/master/specs)。
