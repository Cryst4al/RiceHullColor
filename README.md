# RiceHullColor

RiceHullColor 是一个可复现的水稻颖壳颜色表型分析工具。它把经过 Adobe Camera Raw/Photoshop 全局颜色校正的 `CAL.tif` 或仅裁切的 `ROI.tif`，转换为逐粒、逐图像和逐材料的 CIELAB D50、sRGB 与灰度结果，并同时保存 Fiji/ImageJ 可读取的 ROI、质控叠加图和运行清单。

> 当前版本从 16 位 sRGB TIFF 开始执行定量分析。RAW 的白平衡、镜头校正和 16 位 sRGB 输出仍在 Adobe Camera Raw 中完成；软件不会修改 RAW 感光数据。JPEG 仅允许作演示或试运行，不推荐用于正式分析。

## 主要特点

- 按实际检测到的颖壳数输出，不强制每张图必须有 10 粒；
- 与既有实验口径一致：`a* < -5`、`b* > 5`、`15 <= L* <= 90` 的组织掩膜，并测量每个连通域中央 70%；
- sRGB（D65）先适配到 D50，再计算 CIELAB；平均 Lab 可反算为 sRGB；
- 灰度默认按 `0.299R + 0.587G + 0.114B`（BT.601）计算；
- 输出逐粒 CSV、图像/材料汇总、Excel、多页统计结果、ROI.zip、QC 叠加图和 JSON 审计记录；
- 可通过 YAML 固定阈值、最小面积、最大粒数和中央区域比例；
- 提供命令行与简易桌面图形界面。

## 安装

Windows 用户可在 PowerShell 中进入源码目录并执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install_windows.ps1
```

安装完成后双击 `run_gui.cmd`。也可手动安装：

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
python -m pip install -e .
```

Photoshop LZW/ZIP 压缩的 16 位 TIFF 建议安装完整 TIFF 支持：

```bash
python -m pip install -e ".[tiff]"
```

## 5 分钟快速开始

```bash
ricehullcolor init D:\experiment\HULL
```

把颜色校正母版放入 `02_CAL颜色校正图`，或把仅裁切的图像放入 `03_ROI分析图`。文件名推荐为：

```text
DEMO001-R1-P03-HULL-20260813-I01_ROI.tif
```

分析单张图像：

```bash
ricehullcolor analyze "03_ROI分析图/DEMO001-R1-P03-HULL-20260813-I01_ROI.tif" \
  --project . --config configs/hull_color_global_v1.yml
```

批量分析并生成统一 Excel：

```bash
ricehullcolor batch . --config configs/hull_color_global_v1.yml
ricehullcolor aggregate . --xlsx results/RiceHullColor_summary.xlsx
```

打开图形界面：

```bash
ricehullcolor-gui
```

## 输出

```text
HULL/
├─ 00_RAW原始备份/
├─ 01_RAW工作副本/
├─ 02_CAL颜色校正图/
├─ 03_ROI分析图/
├─ 04_QC预览图/              # ROI轮廓、编号与检测数量
├─ 05_ROI选区/                # Fiji/ImageJ ROI.zip
├─ 06_LAB数据/                # 逐图CSV、总表、运行清单
└─ results/                   # Excel与统计结果
```

逐粒结果保留 `PixelCount`、L*/a*/b* 的均值/中位数/标准差、反算 RGB、灰度、源文件与方法。材料汇总以图像为技术重复：先形成图像均值，再对同一材料的图像均值等权平均；同时保留像素加权字段供追溯。

## 统计分析

准备一个含 `Material`、`Date`、`Group` 和 `Lstar/astar/bstar/Gray` 的材料级 CSV，其中 `Group` 为 `Indica`/`Japonica`：

```bash
ricehullcolor stats data.csv --out results/statistics
```

软件输出：日期校正线性模型、BH-FDR、Hedges' g、PERMANOVA 偏 R²、PCA、L2 正则化 Logistic 回归重复分层交叉验证、AUC/平衡准确率/灵敏度/特异度，以及白底出版级 PNG/PDF。统计单位必须是材料；同一材料的多粒、多图像只能作为技术亚样本，不能直接扩增统计样本量。

## 科学边界

- 本软件量化的是在固定成像和全局颜色校正条件下的表型关联；它不能单独证明遗传因果关系。
- 灰度与 L* 都主要描述明暗，通常高度相关，不应当作两个独立证据重复解释。
- 不同日期合并时应保留 `Date` 并做批次校正或敏感性分析；若材料与日期完全混杂，则不能区分材料效应和日期效应。
- 自动 ROI 必须查看 QC 图。粘连、强反光、阴影、病斑或背景异常时，应在 Fiji/ImageJ 中人工修正 ROI 后再提取。

完整的 Camera Raw 操作规范见 [docs/PHOTOSHOP_ACR_ZH.md](docs/PHOTOSHOP_ACR_ZH.md)，算法与统计口径见 [docs/METHODS_ZH.md](docs/METHODS_ZH.md)。

## 数据隐私

仓库的 `.gitignore` 默认排除 RAW、XMP、各阶段图像和生成结果。发布前请再次检查 `git status`，不要上传含材料标签、个人信息或未公开试验数据的照片。

## 引用与许可

代码使用 Apache-2.0 许可。当前公开作者标识为 GitHub 用户名 `Cryst4al`；如需正式论文署名，请在 `CITATION.cff` 中补充真实姓名和 ORCID。可通过 GitHub Release + Zenodo 归档获得可引用 DOI。

