# RiceHullColor v0.1.0

首个可公开复现的 MVP 版本，将既有水稻颖壳颜色处理方法封装为 Python 命令行和 Windows 图形界面。

## 包含功能

- 标准实验文件夹初始化；
- 16 位 sRGB TIFF 和常见预览图读取；
- sRGB D65 → CIELAB D50；
- 实际粒数连通域识别与中央 70% 组织测量；
- 逐粒 Lab、反算 RGB、BT.601 灰度；
- Fiji/ImageJ ROI.zip、QC 叠加图、JSON 审计清单；
- 图像、材料日期、材料三级汇总和 Excel；
- 日期校正单变量模型、BH-FDR、Hedges' g、PERMANOVA 偏 R²、PCA、重复交叉验证 Logistic 回归；
- 中文 Camera Raw 与统计方法说明；
- Windows 一键安装脚本和 GitHub Actions 测试。

## 已验证

- 6 项自动化测试通过；
- 一张历史 16 位 TIFF 的匿名回归验证中，10 个 ROI 数量、像素数以及 Lab 均值/中位数/标准差与历史脚本逐项一致；
- 发布包不含该验证图像、结果或其他实验数据。

## 已知限制

- RAW 白平衡、光学校正与 16 位 sRGB CAL 输出仍需 Adobe Camera Raw/Photoshop；
- 自动 ROI 依赖背景和成像条件，所有结果必须查看 QC 图；
- 粘连颖壳和复杂背景建议在 Fiji/ImageJ 中人工修正；
- 当前不提供相机 DCP 制作或基于标准色卡真值的自动色彩标定；
- 表型关联不等同于遗传因果。
