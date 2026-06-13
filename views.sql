USE loan_db;

CREATE OR REPLACE VIEW top100_high_risk AS
SELECT id, total, util_score, late_score, age_score, type_score, inq_score,
       segment, annual_inc, dti, revol_bal, revol_util, purpose, loan_status, recommendation
FROM customer_score
WHERE segment = '高風險'
ORDER BY total ASC, annual_inc ASC
LIMIT 100;

CREATE OR REPLACE VIEW top100_premium AS
SELECT id, total, util_score, late_score, age_score, type_score, inq_score,
       segment, annual_inc, dti, revol_bal, revol_util, purpose, loan_status, recommendation
FROM customer_score
WHERE segment = '優質'
ORDER BY total DESC, annual_inc DESC
LIMIT 100;

CREATE OR REPLACE VIEW top100_default AS
SELECT id, total, util_score, late_score, age_score, type_score, inq_score,
       segment, annual_inc, dti, revol_bal, revol_util, purpose, loan_status, recommendation
FROM customer_score
WHERE segment = '違約'
ORDER BY total ASC, annual_inc ASC
LIMIT 100;
