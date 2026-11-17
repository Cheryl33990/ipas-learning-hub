<!--
title: 第 28 題 MAE 外部補證
status: in-review
updated: 2026-11-16
-->

# 第 28 題 MAE 外部補證

結論：官方技術文件可補上 MAE 定義、迴歸評估用途與分類指標差異。這是獨立外部證據筆記，尚未加入雙科教材索引，也未改寫原解析或 v2。外部補證內容由 AI 核對，待人工審查；先前使用者確認的是缺口存在。

## 來源與直接支持範圍

查閱日期：2026-11-16。採用框架維護者的第一手技術文件；scikit-learn 頁面當次顯示 1.9.1，Keras 為 Keras 3 文件。stable 網址會隨版本更新，不視為永久版本鎖定；本機來源摘記在 data/evaluation/mae-external-sources.json，未宣稱已保存整頁快照。

| 識別／來源 | 直接支持 | 不支持的擴張結論 |
|---|---|---|
| E1：[scikit-learn mean_absolute_error](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.mean_absolute_error.html) | MAE 是迴歸損失／評估量；輸入為實際與預測目標值；非負，最佳值為零 | 不證明任何特定應用一定由 MAE 表現最佳 |
| E2：[Keras Regression losses，MeanAbsoluteError](https://keras.io/api/losses/regression_losses/#meanabsoluteerror-class) | MAE 為實際與預測之絕對差的平均；同頁也列 MSE 為平方差平均 | 不表示只有 MAE 可評估迴歸 |
| E3：[scikit-learn accuracy_score](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.accuracy_score.html) | 分類準確率衡量分類正確的比例或數量，輸入為類別標籤 | 不直接量測連續數值的偏差大小 |
| E4：[scikit-learn confusion_matrix](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.confusion_matrix.html) | 按真實類別與預測類別統計樣本數 | 不直接提供連續預測誤差；它是表格，不是單一誤差分數 |
| E5：[scikit-learn LinearRegression](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LinearRegression.html) | 普通最小平方法擬合線性模型，使殘差平方和最小 | 不表示模型只能以平方誤差評估 |

## 定義與自寫示例

單一連續目標、每筆等權重時，MAE = (1/n) × Σ |實際值 − 預測值|。權重及多輸出情況另依定義處理；本題不需要擴張到那些情境。[E1](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.mean_absolute_error.html)、[E2](https://keras.io/api/losses/regression_losses/#meanabsoluteerror-class)。

自造數值示例（非教材或試題數字）：實際值 10、20、30，預測值 12、17、31；絕對差為 2、3、1，MAE 為 2。由公式可推得，MAE 與原目標使用相同單位，高估與低估不會因正負互相抵銷；這是數學推導，不是來源對本題的直接解答。

## 第 28 題的適用判斷

既有教材 S1:3-36:0、S1:3-13:1 已提供監督式學習與連續數值迴歸的核心依據，使用者已確認相關判讀。外部 E1／E2 補上評估環節：對這類連續目標，可把模型的預測值與實際值逐筆比較，以 MAE 表達平均偏離程度。將此一般定義套用到第 28 題屬 AI 情境推論。

E3／E4 的分類評估依賴類別標籤，因此不直接符合本題原本的連續目標。若先離散化目標，評估的是另一個分類任務，不能不說明就替換原任務。這是由指標定義與題目目標推導的比較。

訓練目標與評估指標需分開：E5 的線性迴歸以平方殘差擬合，E1 接收實際與預測數值計算 MAE，因此訓練後使用 MAE 評估是相容的；不需聲稱線性迴歸本身以 MAE 訓練。這是兩份文件綜合推論。

本輪支持「MAE 與監督式連續預測的搭配合理」，不宣稱 MAE 唯一最佳、線性模型在實際資料一定最佳，或其他三組演算法的全部排除理由已在本筆記逐一查證。既有 MAE 缺口可標為「外部來源已備妥、待審與整合」，教材檢索本身仍未包含這份證據。

## 版本、驗證與後續

本 repo 版本為 HEAD 5cf7d96 加既有未提交成果。本輪開啟並核對五份官方頁面的定義／參數／公式，未依搜尋摘要直接下結論。自造示例以 Python 標準函式計算驗證為 2，不安裝或執行 scikit-learn／Keras，也未執行模型或應用測試。資料來源網址與短摘記只在 data/；本文件使用自寫判讀。

官方考綱是否涵蓋 MAE 仍未查證；「相對超綱」維持使用者審查意見。第一輪解析、標準答案、原頁碼評估、v2 標註與索引都不改寫，不能把外部補證算成原教材檢索命中。

下一步可先以這份筆記作外部補證範例，採獨立來源識別、查閱日期、直接支持／推論／限制欄位。若之後決定納入檢索，須另建含外部來源的索引版本與對應評估，保留教材限定基準；本輪未執行該整合。其他缺口仍見[缺口清單](2026-11-16-retrieval-gap-register.md)，第 4、40 題的核心證據可按相同方式逐項處理。
