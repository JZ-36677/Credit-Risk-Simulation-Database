# 信用風險評分與風控儀表板

## 專案簡介

本專案延伸自「信用風險模擬器 v3」，新增**風控後端儀表板**功能：將真實貸款資料批量套用FICO五因素評分邏輯，產出客戶分級名單與對應的業務行動建議，模擬銀行風控/CRM部門的實務工作流程。

兩種使用模式並存：

|模式   |用途             |資料來源           |
|-----|---------------|---------------|
|個人填寫 |公開版，使用者自行測試信用評分|手動輸入           |
|讀取資料庫|風控儀表板，批量分析既有客戶 |MySQL `loan_db`|

新版以獨立GitHub Pages部署，不影響原模擬器網頁。

-----

## 資料來源

|資料表               |筆數     |來源                |用途        |
|------------------|-------|------------------|----------|
|`loan_data`       |850,243|LendingClub個人信貸資料集|主要評分對象    |
|`credit_card_data`|29,089 |UCI信用卡違約資料集       |待定（統計分析素材）|

兩個資料集來源不同、無共同ID，不混為同一客戶池，各自獨立呈現。

-----

## 評分邏輯（5因素加權，總分300–850）

|因素   |權重 |資料來源                                                              |說明                                |
|-----|---|------------------------------------------------------------------|----------------------------------|
|還款紀錄 |35%|`delinq_2yrs`／`pub_rec`／`collections_12_mths_ex_med`／`loan_status`|多欄位疊加扣分，詳見下表                      |
|額度使用率|30%|`revol_util`                                                      |套用原模擬器`getUtilScore()`對照表（440–760）|
|信用年齡 |15%|`earliest_cr_line`、`issue_d`                                      |兩者相差年數，分5級（-45 ~ +15）             |
|信用種類 |10%|`dti`、`purpose`                                                   |dti分桶＋`debt_consolidation`特例，詳見下表 |
|新申請次數|10%|`inq_last_6mths`                                                  |分5級（+5 ~ -35），沿用原模擬器規則            |

`total = clamp(基礎分(使用率) + 還款紀錄總分 + 信用年齡 + 信用種類 + 申請次數, 300, 850)`

### 還款紀錄細項

|條件                              |扣分           |
|--------------------------------|-------------|
|`delinq_2yrs` = 0／1／2-3／≥4      |0／-30／-60／-88|
|`pub_rec` > 0                   |額外 -20       |
|`collections_12_mths_ex_med` > 0|額外 -15       |
|`loan_status` = Late(31-120天)   |額外 -30       |
|`loan_status` = Late(16-30天)    |額外 -10       |

### 信用種類細項

|`purpose`          |`dti`|分數 |備註                            |
|-------------------|-----|---|------------------------------|
|任意                 |< 15 |20 |最高分                           |
|非debt_consolidation|≥ 15 |10 |信用卡＋貸款用途＝2種基礎                 |
|debt_consolidation |15–36|10 |一半分數                          |
|debt_consolidation |≥ 36 |-10|**強制歸高風險**（override，不論total分數）|

-----

## 客群分類

|客群   |判定條件                                                                  |
|-----|----------------------------------------------------------------------|
|🔴 高風險|`total`<580 OR `annual_inc`<`revol_bal` OR （debt_consolidation且dti≥36）|
|🟢 優質 |`total`≥700 AND `annual_inc`>`revol_bal`                              |
|⚫ 違約 |`loan_status` ∈ {Charged Off, Default}（獨立判定，優先於上述兩者）                  |
|⚪ 正常 |以上皆非，不進榜                                                              |

-----

## 行動建議（Step4，依客群自動產生）

|客群                               |建議內容                                                |
|---------------------------------|----------------------------------------------------|
|違約                               |轉法務／委外催收，評估呆帳轉銷                                     |
|高風險（debt_consolidation且total<580）|已整合仍高風險，優先轉催收                                       |
|高風險（其他）                          |聯繫客戶提醒還款，提供個人信貸整合方案（整合利率≈int_rate，目前循環利率≈revol_util）|
|優質                               |聯繫客戶說明低利率最低還款／信貸槓桿方案，維持循環餘額對評分無影響                   |
|正常                               |不產生待辦                                               |

-----

## 系統架構

- **前端**：GitHub Pages（新建repo，與原模擬器分開）
- **資料庫**：GCP VM + MySQL 8.0（`loan_db`）
- **批次評分**：對`loan_data`逐筆計算5因素分數，寫入`customer_score`表
- **三榜查詢**：高風險／優質／違約 各TOP100，依`total`排序，同分依`annual_inc`排序

```
customer_score 表欄位：
id, total, late_score, util_score, age_score, type_score, inq_score,
客群, annual_inc, dti, revol_bal, revol_util, purpose, loan_status, 建議文字
```

```sql
高風險TOP100 = WHERE 客群='高風險' ORDER BY total ASC,  annual_inc ASC  LIMIT 100
優質TOP100   = WHERE 客群='優質'   ORDER BY total DESC, annual_inc DESC LIMIT 100
違約TOP100   = WHERE 客群='違約'   ORDER BY total ASC,  annual_inc ASC  LIMIT 100
```

-----

## 開發狀態

- [x] 資料庫欄位確認（`loan_data` / `credit_card_data`）
- [x] 評分邏輯與分桶規則定案
- [x] 客群分類與行動建議邏輯定案
- [ ] 批次評分腳本（SQL/Python）
- [ ] `customer_score`表建立
- [ ] 三榜TOP100查詢實作
- [ ] 儀表板前端開發
- [ ] `credit_card_data`定位決策（獨立頁籤／統計素材）