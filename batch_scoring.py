"""
batch_scoring.py
讀取 loan_data，套用5因素評分邏輯，寫入 customer_score 表

使用方式：
  python3 batch_scoring.py --sample 10
      → 只抓前10筆，印出計算結果，不寫入DB（先用這個確認邏輯對不對）

  python3 batch_scoring.py
      → 正式跑全部850K筆，建表並寫入customer_score

前置需求：
  - pip3 install pymysql --break-system-packages
  - ~/.my.cnf 已設定好帳密（之前已確認可用）
"""
import argparse
import os
import pymysql
import pymysql.cursors

from scoring_logic import score_one, to_float


MY_CNF = os.path.expanduser('~/.my.cnf')

DB_CONFIG = dict(
    host='localhost',
    database='loan_db',
    read_default_file=MY_CNF,
    charset='utf8mb4',
)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS customer_score (
    id VARCHAR(64) PRIMARY KEY,
    total INT,
    util_score INT,
    late_score INT,
    age_score INT,
    type_score INT,
    inq_score INT,
    segment VARCHAR(10),
    annual_inc DOUBLE,
    dti DOUBLE,
    revol_bal DOUBLE,
    revol_util DOUBLE,
    purpose VARCHAR(64),
    loan_status VARCHAR(64),
    recommendation VARCHAR(255),
    INDEX idx_segment (segment),
    INDEX idx_total (total)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

INSERT_SQL = """
INSERT INTO customer_score
    (id, total, util_score, late_score, age_score, type_score, inq_score,
     segment, annual_inc, dti, revol_bal, revol_util, purpose, loan_status, recommendation)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
ON DUPLICATE KEY UPDATE
    total=VALUES(total), util_score=VALUES(util_score), late_score=VALUES(late_score),
    age_score=VALUES(age_score), type_score=VALUES(type_score), inq_score=VALUES(inq_score),
    segment=VALUES(segment), annual_inc=VALUES(annual_inc), dti=VALUES(dti),
    revol_bal=VALUES(revol_bal), revol_util=VALUES(revol_util), purpose=VALUES(purpose),
    loan_status=VALUES(loan_status), recommendation=VALUES(recommendation);
"""

BATCH_SIZE = 2000


def row_to_insert_tuple(row, result):
    return (
        row['id'],
        result['total'], result['util_score'], result['late_score'],
        result['age_score'], result['type_score'], result['inq_score'],
        result['segment'],
        to_float(row.get('annual_inc')),
        to_float(row.get('dti')),
        to_float(row.get('revol_bal')),
        to_float(row.get('revol_util')),
        row.get('purpose'),
        row.get('loan_status'),
        result['recommendation'],
    )


def run_sample(n):
    conn = pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)
    cur = conn.cursor()
    cur.execute("SELECT * FROM loan_data LIMIT %s", (n,))
    rows = cur.fetchall()
    conn.close()

    print(f"取樣 {len(rows)} 筆，計算結果如下：\n")
    for row in rows:
        result = score_one(row)
        print(f"id={row.get('id')}")
        print(f"  原始值: revol_util={row.get('revol_util')!s:>8}  dti={row.get('dti')!s:>6}  "
              f"annual_inc={row.get('annual_inc')!s:>10}  revol_bal={row.get('revol_bal')!s:>10}  "
              f"loan_status={row.get('loan_status')!s:<20}  purpose={row.get('purpose')}")
        print(f"  子分數: util={result['util_score']} late={result['late_score']} "
              f"age={result['age_score']} type={result['type_score']} inq={result['inq_score']}")
        print(f"  => total={result['total']}  segment={result['segment']}  "
              f"建議={result['recommendation']}")
        print()


def run_full():
    read_conn = pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.SSDictCursor)
    write_conn = pymysql.connect(**DB_CONFIG)

    write_cur = write_conn.cursor()
    write_cur.execute(CREATE_TABLE_SQL)
    write_conn.commit()

    read_cur = read_conn.cursor()
    read_cur.execute("SELECT * FROM loan_data")

    batch = []
    total_count = 0
    segment_counts = {'優質': 0, '高風險': 0, '違約': 0, '正常': 0}

    for row in read_cur:
        result = score_one(row)
        segment_counts[result['segment']] += 1
        batch.append(row_to_insert_tuple(row, result))

        if len(batch) >= BATCH_SIZE:
            write_cur.executemany(INSERT_SQL, batch)
            write_conn.commit()
            total_count += len(batch)
            print(f"已處理 {total_count} 筆...")
            batch = []

    if batch:
        write_cur.executemany(INSERT_SQL, batch)
        write_conn.commit()
        total_count += len(batch)

    print(f"\n完成！總共 {total_count} 筆")
    print(f"客群分布: {segment_counts}")

    read_conn.close()
    write_conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--sample', type=int, default=0,
                         help='只測試前N筆並印出結果，不寫入DB')
    args = parser.parse_args()

    if args.sample > 0:
        run_sample(args.sample)
    else:
        run_full()
