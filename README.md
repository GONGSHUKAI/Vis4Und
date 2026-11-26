# Vis4Und

Visualize for Understanding：机器人学习研究要补的预备知识，每个专题一个可视化网页。

在线浏览：https://gongshukai.github.io/Vis4Und/

## 专题

下面的列表由 `tools/build.py` 根据 `catalog.json` 生成，不要手改。

<!-- catalog:start -->
### (1) 机器人学

- (i) [旋转与位姿表示](https://gongshukai.github.io/Vis4Und/pages/rotations/) — 旋转矩阵、欧拉角、轴角、四元数、6D 表示和齐次变换：定义、互相换算、插值，以及网络该输出哪一种。
- (ii) [机器人的运动空间](https://gongshukai.github.io/Vis4Und/pages/action-space/) — 关节空间与末端空间、绝对动作与增量动作、正运动学、雅可比与逆运动学；VLA 的动作到底在哪个空间里。
- (iii) [相机模型与标定](https://gongshukai.github.io/Vis4Und/pages/camera/) — 针孔模型、内参与畸变、外参、各家坐标系约定、张正友标定、手眼标定和深度反投影。
- (iv) [π 系列 VLA](https://gongshukai.github.io/Vis4Und/pages/pi-series/) — flow matching 动作专家、FAST 动作 token、π0.5 的异构数据与分层推理、知识隔离，以及 π*0.6 用优势条件化做 RL。
- (v) [实时分块执行（RTC）](https://gongshukai.github.io/Vis4Und/pages/rtc/) — 推理有延迟时动作块怎么衔接：同步执行、时间集成、异步队列，推理期 RTC 的冻结前缀与软掩码引导，训练期 RTC 的前缀条件化。
- (vi) [仿真 RL 与行为克隆](https://gongshukai.github.io/Vis4Und/pages/sim-rl/) — 仿真 RL 具体怎么做（并行环境、奖励、域随机化、教师-学生蒸馏），为什么要做，和采数据训 VLA 的行为克隆差在哪里，以及两者怎么结合。

### (2) 3D 视觉与图形学

- (i) [3D 表征](https://gongshukai.github.io/Vis4Und/pages/3d-representations/) — 深度图、点云、体素、网格、SDF、NeRF 和 3D 高斯：各自存什么、怎么互相转换、什么任务该用哪种。
- (ii) [SLAM](https://gongshukai.github.io/Vis4Und/pages/slam/) — 边走边定位边建图：前端里程计、后端因子图与光束法平差、回环检测，以及学习式和高斯式 SLAM 的近年进展。
- (iii) [3D 基础模型](https://gongshukai.github.io/Vis4Und/pages/3d-foundation-models/) — 前馈式重建（DUSt3R、VGGT 一系）、单目几何估计，以及 3D 物体与场景生成。

### (3) Agentic RL

- (i) [LLM 强化学习基础](https://gongshukai.github.io/Vis4Und/pages/llm-rl-basics/) — 从策略梯度到 PPO、GRPO 及其变体：把一次生成看成一条轨迹，奖励怎么变成每个 token 的梯度。
- (ii) [Coding Agent 的训练](https://gongshukai.github.io/Vis4Und/pages/coding-agent/) — 多轮工具调用的轨迹、可执行环境与测试奖励、SFT 冷启动加多轮 RL，以及几套经典开源实现。
- (iii) [Robot-Use Agent 的训练](https://gongshukai.github.io/Vis4Und/pages/robot-use-agent/) — 让推理模型像操作电脑一样直接操作机器人：动作接口、仿真里只用成功信号的 RL（PEAR），和把动作写成语义步骤的 SFT（nanoAstra）。

### (4) 分布式训练

- (i) [训练的显存与算力账](https://gongshukai.github.io/Vis4Und/pages/gpu-memory-flops/) — GPU 的存储层级与 roofline，一步训练要多少 FLOPs、MFU 怎么算，参数 / 梯度 / 优化器状态 / 激活各占多少显存，以及重计算和梯度累积。
- (ii) [数值精度与混合精度](https://gongshukai.github.io/Vis4Und/pages/numerics/) — FP32 / TF32 / FP16 / BF16 / FP8 / MXFP8 / MXFP4 / NVFP4 的位布局与取值范围，混合精度训练、loss scaling、FP8 与块缩放、随机舍入。
- (iii) [集合通信](https://gongshukai.github.io/Vis4Und/pages/collectives/) — broadcast、reduce、all-reduce、all-gather、reduce-scatter、all-to-all 的语义与通信量，ring 与 tree 算法的 α-β 代价，NVLink / InfiniBand 拓扑与 NCCL。
- (iv) [优化器：从 Adam 到 Muon](https://gongshukai.github.io/Vis4Und/pages/optimizers/) — 动量 SGD、Adam、AdamW 的更新与状态，学习率调度与梯度裁剪，Muon 的 Newton–Schulz 正交化及其在大模型上的用法。
- (v) [FlashAttention 系列](https://gongshukai.github.io/Vis4Und/pages/flash-attention/) — 标准 attention 的显存读写瓶颈，online softmax 与分块，FlashAttention 1 / 2 / 3 / 4 各改了什么，以及 Flash-Decoding 和变长、掩码变体。
- (vi) [并行策略](https://gongshukai.github.io/Vis4Und/pages/parallelism/) — 数据并行与 ZeRO / FSDP / HSDP，张量并行与序列并行，流水线的 GPipe / 1F1B / 交错 / Zero Bubble / DualPipe，上下文并行（Ring Attention、Ulysses），MoE 的专家并行与 ETP，以及多维组合与配置估算。
<!-- catalog:end -->

## 添加专题

页面规范见 [docs/page-spec.md](docs/page-spec.md)，骨架见 [docs/template.html](docs/template.html)。

```bash
python3 tools/build.py            # 生成首页、导航、README 列表，检查断链
python3 tools/shot.py pages/<slug>/ --full   # 截桌面 / 手机 × 深 / 浅四张图（需要 websocket-client）
```
