"""
信用評分核心邏輯
這個檔案只放「純函式」(不連DB)，方便獨立測試
"""
from datetime import datetime


# ──────────────────────────────
# 工具函式：安全轉數字
# ──────────────────────────────
def to_float(val, default=0.0):
    if val is None:
        return default
    s = str(val).strip().replace('%', '').replace(',', '')
    if s == '' or s.lower() in ('n/a', 'nan', 'none'):
        return default
    try:
        return float(s)
    except ValueError:
        return default


def to_int(val, default=0):
    return int(to_float(val, default))


def parse_date(val):
    """寬鬆解析日期字串，失敗回傳 None
    LendingClub格式通常是 'Mon-YYYY' 或 'Mon-YY'，
    依序嘗試常見格式，避免2位數年份被誤判。
    """
    if val is None:
        return None
    s = str(val).strip()
    if s == '' or s.lower() in ('n/a', 'nan', 'none'):
        return None
    for fmt in ('%b-%Y', '%b-%y', '%Y-%m-%d', '%m/%d/%Y', '%Y-%m'):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


# ──────────────────────────────
# 因素1：額度使用率 30%（基礎分）
# ──────────────────────────────
def get_util_score(util):
    if util <= 0:  return 750
    if util <= 5:  return 755
    if util <= 10: return 760
    if util <= 20: return 745
    if util <= 30: return 720
    if util <= 40: return 690
    if util <= 50: return 655
    if util <= 60: return 615
    if util <= 75: return 570
    if util <= 90: return 525
    if util <= 99: return 480
    return 440


# ──────────────────────────────
# 因素2：還款紀錄 35%
# ──────────────────────────────
def get_late_score(row):
    delinq = to_float(row.get('delinq_2yrs'), 0)
    if delinq == 0:
        score = 0
    elif delinq == 1:
        score = -30
    elif delinq <= 3:
        score = -60
    else:
        score = -88

    if to_float(row.get('pub_rec'), 0) > 0:
        score -= 20

    if to_float(row.get('collections_12_mths_ex_med'), 0) > 0:
        score -= 15

    status = str(row.get('loan_status') or '')
    if 'Late (31-120' in status:
        score -= 30
    elif 'Late (16-30' in status:
        score -= 10

    return score


# ──────────────────────────────
# 因素3：信用年齡 15%
# ──────────────────────────────
def get_age_score(row):
    earliest = parse_date(row.get('earliest_cr_line'))
    issue = parse_date(row.get('issue_d'))
    if earliest is None or issue is None:
        return -10  # 對應原網頁「不確定」選項

    years = (issue - earliest).days / 365.25
    if years < 1:
        return -45
    elif years < 3:
        return -25
    elif years < 7:
        return -10
    elif years < 15:
        return 0
    else:
        return 15


# ──────────────────────────────
# 因素4：信用種類 10%（dti + purpose）
# 回傳 (分數, 是否強制歸高風險)
# ──────────────────────────────
def get_type_score_and_override(row):
    dti_raw = row.get('dti')
    dti = to_float(dti_raw, None) if dti_raw not in (None, '') else None
    purpose = str(row.get('purpose') or '')

    if dti is not None and dti < 15:
        return 20, False

    if purpose == 'debt_consolidation':
        if dti is not None and dti >= 36:
            return -10, True
        return 10, False

    return 10, False


# ──────────────────────────────
# 因素5：新申請次數 10%
# ──────────────────────────────
def get_inq_score(row):
    inq = to_float(row.get('inq_last_6mths'), 0)
    if inq == 0:
        return 5
    elif inq == 1:
        return 0
    elif inq <= 3:
        return -10
    elif inq <= 5:
        return -20
    else:
        return -35


# ──────────────────────────────
# 整合：算出一筆客戶的完整結果
# ──────────────────────────────
def score_one(row):
    util = to_float(row.get('revol_util'), 0)
    base = get_util_score(util)
    late = get_late_score(row)
    age = get_age_score(row)
    type_score, override = get_type_score_and_override(row)
    inq = get_inq_score(row)

    total = base + late + age + type_score + inq
    total = max(300, min(850, total))

    segment = classify(row, total, override)
    recommendation = get_recommendation(segment, row, total)

    return {
        'total': total,
        'util_score': base,
        'late_score': late,
        'age_score': age,
        'type_score': type_score,
        'inq_score': inq,
        'segment': segment,
        'recommendation': recommendation,
    }


# ──────────────────────────────
# 客群分類
# ──────────────────────────────
def classify(row, total, override):
    annual_inc = to_float(row.get('annual_inc'), 0)
    revol_bal = to_float(row.get('revol_bal'), 0)
    loan_status = str(row.get('loan_status') or '')

    if loan_status in ('Charged Off', 'Default'):
        return '違約'
    if total < 580 or annual_inc < revol_bal or override:
        return '高風險'
    if total >= 700 and annual_inc > revol_bal:
        return '優質'
    return '正常'


# ──────────────────────────────
# Step4 行動建議
# ──────────────────────────────
def get_recommendation(segment, row, total):
    purpose = str(row.get('purpose') or '')

    if segment == '違約':
        return '轉法務/委外催收，評估呆帳轉銷'
    if segment == '高風險':
        if purpose == 'debt_consolidation' and total < 580:
            return '已整合仍高風險，優先轉催收'
        return '聯繫客戶提醒還款，提供個人信貸整合方案'
    if segment == '優質':
        return '聯繫客戶說明低利率最低還款/信貸槓桿方案'
    return None
