# 希可 Live2D 骨架 v06（露娜）

- `seeko_v06b.cmo3`：在 v05 基础上，转头和身体的幅度加大、脸部做了圆柱投影（立体感），加了左右臂抬起参数。
- `caff.py` / `model.py`：读写 .cmo3（CAFF 容器：单字节 XOR + 里面一个只有本地头和数据描述符的 zip），以及解析变形器、关键形态网格。
- `rig_v06.py`：用代码改关键形态坐标的脚本（`python3 rig_v06.py 输入.cmo3 输出.cmo3`）。改完的文件 Cubism 5.3 能正常打开。
- `l2d_motions_v2.py`：生成待机和动作的 motion3.json。
