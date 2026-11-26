# Vis4Und

Visualize for Understanding：机器人学习研究要补的预备知识，每个专题一个可视化网页。

在线浏览：https://gongshukai.github.io/Vis4Und/

## 专题

下面的列表由 `tools/build.py` 根据 `catalog.json` 生成，不要手改。

<!-- catalog:start -->
### (1) 机器人学

- 补充 [旋转与位姿表示](https://gongshukai.github.io/Vis4Und/pages/rotations/) — 旋转矩阵、欧拉角、轴角、四元数、6D 表示和齐次变换：定义、互相换算、插值，以及网络该输出哪一种。
- (i) [机器人的运动空间](https://gongshukai.github.io/Vis4Und/pages/action-space/) — 关节空间与末端空间、绝对动作与增量动作、正运动学、雅可比与逆运动学；VLA 的动作到底在哪个空间里。
- (ii) [相机模型与标定](https://gongshukai.github.io/Vis4Und/pages/camera/) — 针孔模型、内参与畸变、外参、各家坐标系约定、张正友标定、手眼标定和深度反投影。

### (2) 3D 视觉与图形学

- (i) [3D 表征](https://gongshukai.github.io/Vis4Und/pages/3d-representations/) — 深度图、点云、体素、网格、SDF、NeRF 和 3D 高斯：各自存什么、怎么互相转换、什么任务该用哪种。
- (ii) [SLAM](https://gongshukai.github.io/Vis4Und/pages/slam/) — 边走边定位边建图：前端里程计、后端因子图与光束法平差、回环检测，以及学习式和高斯式 SLAM 的近年进展。
- (iii) [3D 基础模型](https://gongshukai.github.io/Vis4Und/pages/3d-foundation-models/) — 前馈式重建（DUSt3R、VGGT 一系）、单目几何估计，以及 3D 物体与场景生成。

### (3) Agentic RL

- 补充 [LLM 强化学习基础](https://gongshukai.github.io/Vis4Und/pages/llm-rl-basics/) — 从策略梯度到 PPO、GRPO 及其变体：把一次生成看成一条轨迹，奖励怎么变成每个 token 的梯度。
- (i) [Coding Agent 的训练](https://gongshukai.github.io/Vis4Und/pages/coding-agent/) — 多轮工具调用的轨迹、可执行环境与测试奖励、SFT 冷启动加多轮 RL，以及几套经典开源实现。
- (ii) [Robot-Use Agent 的训练](https://gongshukai.github.io/Vis4Und/pages/robot-use-agent/) — 让推理模型像操作电脑一样直接操作机器人：动作接口、仿真里只用成功信号的 RL（PEAR），和把动作写成语义步骤的 SFT（nanoAstra）。
<!-- catalog:end -->

## 添加专题

页面规范见 [docs/page-spec.md](docs/page-spec.md)，骨架见 [docs/template.html](docs/template.html)。

```bash
python3 tools/build.py            # 生成首页、导航、README 列表，检查断链
python3 tools/shot.py pages/<slug>/ --full   # 截桌面 / 手机 × 深 / 浅四张图（需要 websocket-client）
```
