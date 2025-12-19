"""
한국 경제 위기 지수 - 데이터 수집 스크립트
==========================================
한국은행 ECOS API 및 기타 공공 데이터에서 경제 지표 수집
"""

import os
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path

# API 키 (GitHub Secrets에서 가져오기)
ECOS_API_KEY = os.environ.get("ECOS_API_KEY", "sample")

# 기본 URL
ECOS_BASE_URL = "https://ecos.bok.or.kr/api"

# 데이터 저장 경로
DATA_PATH = Path(__file__).parent.parent / "data" / "indicators.json"


def get_ecos_data(stat_code, item_code, start_date, end_date, cycle="D"):
    """한국은행 ECOS API에서 데이터 조회"""
    url = f"{ECOS_BASE_URL}/StatisticSearch/{ECOS_API_KEY}/json/kr/1/1/{stat_code}/{cycle}/{start_date}/{end_date}/{item_code}"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if "StatisticSearch" in data:
            row = data["StatisticSearch"]["row"][0]
            return {
                "value": float(row["DATA_VALUE"]),
                "date": row["TIME"],
                "name": row["ITEM_NAME1"]
            }
    except Exception as e:
        print(f"ECOS API 오류 ({stat_code}): {e}")
    
    return None


def get_exchange_rate():
    """환율 데이터 (USD/KRW)"""
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")
    
    # ECOS: 원/달러 환율 (매매기준율)
    result = get_ecos_data("731Y001", "0000001", start_date, end_date, "D")
    
    if result:
        return {
            "value": result["value"],
            "date": result["date"],
            "source": "한국은행"
        }
    
    # 실패시 기본값
    return {"value": 1450.0, "date": end_date, "source": "기본값"}


def get_bond_rate_3y():
    """국고채 3년 금리"""
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")
    
    # ECOS: 국고채(3년) 금리
    result = get_ecos_data("817Y002", "010200000", start_date, end_date, "D")
    
    if result:
        return {
            "value": result["value"],
            "date": result["date"],
            "source": "한국은행"
        }
    
    return {"value": 2.8, "date": end_date, "source": "기본값"}


def get_foreign_reserve():
    """외환보유액 (월간)"""
    end_date = datetime.now().strftime("%Y%m")
    start_date = (datetime.now() - timedelta(days=90)).strftime("%Y%m")
    
    # ECOS: 외환보유액
    result = get_ecos_data("732Y001", "99", start_date, end_date, "M")
    
    if result:
        return {
            "value": result["value"],
            "date": result["date"],
            "source": "한국은행"
        }
    
    return {"value": 4150.0, "date": end_date, "source": "기본값"}


def get_us_federal_rate():
    """미국 연방기금금리 (FRED API)"""
    # FRED API는 키 없이도 일부 데이터 조회 가능
    try:
        # 미국 연준 기준금리 상단 (현재 4.5%)
        url = "https://api.stlouisfed.org/fred/series/observations"
        params = {
            "series_id": "DFEDTARU",  # Federal Funds Target Range - Upper Limit
            "api_key": "DEMO_API",  # 데모키로도 제한적 조회 가능
            "file_type": "json",
            "sort_order": "desc",
            "limit": 1
        }
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if "observations" in data and len(data["observations"]) > 0:
            obs = data["observations"][0]
            return {
                "value": float(obs["value"]),
                "date": obs["date"]
            }
    except Exception as e:
        print(f"FRED API 오류: {e}")

    # 실패시 현재 미국 금리 (2024년 12월 기준 4.5%)
    return {"value": 4.5, "date": datetime.now().strftime("%Y-%m-%d")}


def get_foreign_net_selling():
    """외국인 순매도 (코스피 - KRX 데이터)"""
    try:
        # 한국거래소 정보데이터시스템 API
        # 외국인 순매매 추이 조회
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")

        url = "http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        # 투자자별 거래실적 (외국인)
        payload = {
            "bld": "dbms/MDC/STAT/standard/MDCSTAT02301",
            "strtDd": start_date,
            "endDd": end_date,
            "inqTpCd": "1",  # 일별
            "trdVolVal": "2",  # 거래대금
            "askBid": "3",  # 순매수
            "share": "1",
            "money": "1",
            "csvxls_is498": "false"
        }

        response = requests.post(url, data=payload, headers=headers, timeout=15)
        data = response.json()

        if "OutBlock_1" in data and len(data["OutBlock_1"]) > 0:
            # 월간 합계 계산 (단위: 백만원 -> 조원)
            total = 0
            for row in data["OutBlock_1"]:
                # 외국인 순매수 금액 (FORN_NETBID_AMT)
                val = row.get("FORN_NETBID_AMT", "0").replace(",", "")
                if val and val != "-":
                    total += float(val)

            # 백만원 -> 조원 변환
            total_trillion = total / 1000000

            return {
                "value": round(total_trillion, 2),
                "date": datetime.now().strftime("%Y.%m"),
                "source": "한국거래소"
            }
    except Exception as e:
        print(f"KRX API 오류: {e}")

    # 실패시 ECOS API로 외국인 증권투자 조회 시도
    try:
        end_date = datetime.now().strftime("%Y%m")
        start_date = (datetime.now() - timedelta(days=60)).strftime("%Y%m")

        result = get_ecos_data("908Y001", "S7A", start_date, end_date, "M")
        if result:
            # 억달러 -> 조원 환산 (환율 1400 가정)
            value_trillion = (result["value"] * 1400) / 10000
            return {
                "value": round(value_trillion, 2),
                "date": result["date"],
                "source": "한국은행"
            }
    except Exception as e:
        print(f"ECOS 외국인투자 조회 오류: {e}")

    # 최종 실패시 기본값
    return {
        "value": -5.0,
        "date": datetime.now().strftime("%Y.%m"),
        "source": "기본값",
        "manual": True
    }


def get_pf_delinquency():
    """PF 연체율 (분기별, 수동 업데이트)"""
    # 금융감독원 보도자료에서 수동 확인 필요
    return {
        "value": 4.49,
        "date": "2025.Q1",
        "source": "금융감독원",
        "manual": True
    }


def get_available_fx_ratio():
    """가용외환비율 (자동 계산)"""
    # 외환보유액 중 즉시 사용 가능한 비율
    # 가용외환 = 총 외환보유액 - 예치금/유가증권 중 유동성 낮은 부분
    # 한국은행 데이터 기반 추정 계산

    try:
        end_date = datetime.now().strftime("%Y%m")
        start_date = (datetime.now() - timedelta(days=90)).strftime("%Y%m")

        # 총 외환보유액
        total_fx = get_ecos_data("732Y001", "99", start_date, end_date, "M")

        # 유가증권 (외환보유액 중)
        securities = get_ecos_data("732Y001", "1000000", start_date, end_date, "M")

        # 예치금
        deposits = get_ecos_data("732Y001", "2000000", start_date, end_date, "M")

        if total_fx and securities:
            # 유가증권 중 약 70%가 즉시 유동화 가능하다고 가정
            # 예치금은 대부분 유동성 높음
            total = total_fx["value"]
            liquid_securities = securities["value"] * 0.7 if securities else 0
            liquid_deposits = deposits["value"] if deposits else 0

            # 가용외환비율 = (유동성 자산 / 총 외환보유액) * 100
            # 실제로는 IMF 적정 외환보유액 대비 비율로 계산
            # IMF 기준 적정 외환보유액 약 6,800억 달러 (한국 기준)
            imf_adequate = 6800

            available_ratio = (total / imf_adequate) * 100

            return {
                "value": round(available_ratio, 1),
                "date": total_fx["date"],
                "source": "한국은행(계산)"
            }
    except Exception as e:
        print(f"가용외환비율 계산 오류: {e}")

    # 실패시 기본값
    return {
        "value": 6.1,
        "date": datetime.now().strftime("%Y.%m"),
        "source": "기본값",
        "manual": True
    }


def get_fx_to_gdp_ratio():
    """GDP 대비 외환보유율 (자동 계산)"""
    try:
        end_date = datetime.now().strftime("%Y%m")
        start_date = (datetime.now() - timedelta(days=90)).strftime("%Y%m")

        # 외환보유액 조회 (억 달러)
        fx_reserve = get_ecos_data("732Y001", "99", start_date, end_date, "M")

        # GDP 조회 (ECOS: 명목 GDP, 분기)
        gdp_end = datetime.now().strftime("%Y") + "Q" + str((datetime.now().month - 1) // 3 + 1)
        gdp_start = str(int(datetime.now().strftime("%Y")) - 1) + "Q1"

        gdp_result = get_ecos_data("200Y001", "10101", gdp_start.replace("Q", ""), gdp_end.replace("Q", ""), "Q")

        if fx_reserve:
            # 한국 GDP 약 1.7조 달러 (2024년 기준)
            # 외환보유액 / GDP * 100
            gdp_usd = 1700000  # 백만 달러 단위
            if gdp_result:
                # 원화 GDP를 달러로 환산 (환율 1350 가정)
                gdp_usd = gdp_result["value"] / 1350

            # 외환보유액은 억달러 -> 백만달러 변환
            fx_million = fx_reserve["value"] * 100

            ratio = (fx_million / gdp_usd) * 100

            # 현재 분기 계산
            quarter = (datetime.now().month - 1) // 3 + 1

            return {
                "value": round(ratio, 1),
                "date": f"{datetime.now().year}.Q{quarter}",
                "source": "한국은행(계산)"
            }
    except Exception as e:
        print(f"GDP 대비 외환보유율 계산 오류: {e}")

    # 실패시 기본값
    return {
        "value": 24.4,
        "date": f"{datetime.now().year}.Q{(datetime.now().month - 1) // 3 + 1}",
        "source": "기본값",
        "manual": True
    }


def get_base_rate():
    """한국 기준금리"""
    end_date = datetime.now().strftime("%Y%m")
    start_date = (datetime.now() - timedelta(days=60)).strftime("%Y%m")
    
    # ECOS: 한국은행 기준금리
    result = get_ecos_data("722Y001", "0101000", start_date, end_date, "M")
    
    if result:
        return {
            "value": result["value"],
            "date": result["date"],
            "source": "한국은행"
        }
    
    return {"value": 3.0, "date": end_date, "source": "기본값"}


def get_korea_us_rate_gap():
    """한미 금리차 (자동 계산)"""
    # 한국 기준금리 - 미국 기준금리
    # 마이너스면 자본 유출 압력
    try:
        korea_rate = get_base_rate()
        us_rate = get_us_federal_rate()

        gap = korea_rate["value"] - us_rate["value"]

        return {
            "value": round(gap, 2),
            "date": datetime.now().strftime("%Y.%m"),
            "source": "한국은행/FRED(계산)"
        }
    except Exception as e:
        print(f"한미 금리차 계산 오류: {e}")

    return {
        "value": -1.5,
        "date": datetime.now().strftime("%Y.%m"),
        "source": "기본값",
        "manual": True
    }


def calculate_risk_level(indicator_name, value, config):
    """위험 수준 계산"""
    danger_high = config["danger_high"]
    danger_low = config["danger_low"]
    reverse = config.get("reverse", True)
    
    if reverse:  # 높을수록 위험
        if value >= danger_high:
            return "danger", "위험"
        elif value >= (danger_low + danger_high) / 2:
            return "warning", "주의"
        else:
            return "safe", "안전"
    else:  # 낮을수록 위험
        if value <= danger_low:
            return "danger", "위험"
        elif value <= (danger_low + danger_high) / 2:
            return "warning", "주의"
        else:
            return "safe", "안전"


def fetch_all_indicators():
    """모든 지표 수집"""
    
    # 지표 설정
    configs = {
        "exchange_rate": {
            "name": "환율 (USD/KRW)",
            "unit": "원",
            "min": 1200,
            "max": 1600,
            "danger_low": 1250,
            "danger_high": 1400,
            "reverse": True,
            "description": "1,400원 이상: 위험"
        },
        "bond_rate_3y": {
            "name": "국고채 3년 금리",
            "unit": "%",
            "min": 1.0,
            "max": 5.0,
            "danger_low": 2.0,
            "danger_high": 3.5,
            "reverse": True,
            "description": "3.5% 이상: 위험"
        },
        "available_fx_ratio": {
            "name": "가용외환비율",
            "unit": "%",
            "min": 0,
            "max": 20,
            "danger_low": 8,
            "danger_high": 12,
            "reverse": False,
            "description": "8% 이하: 위험"
        },
        "fx_to_gdp_ratio": {
            "name": "GDP 대비 외환보유율",
            "unit": "%",
            "min": 10,
            "max": 40,
            "danger_low": 20,
            "danger_high": 30,
            "reverse": False,
            "description": "20% 이하: 주의"
        },
        "korea_us_rate_gap": {
            "name": "한미 금리차",
            "unit": "%p",
            "min": -3.0,
            "max": 2.0,
            "danger_low": -1.0,
            "danger_high": 0.5,
            "reverse": False,
            "description": "-1%p 이하: 자본유출 압력"
        },
        "pf_delinquency": {
            "name": "PF 연체율",
            "unit": "%",
            "min": 0,
            "max": 10,
            "danger_low": 2,
            "danger_high": 5,
            "reverse": True,
            "description": "5% 이상: 위험"
        },
        "foreign_net_selling": {
            "name": "외국인 순매도",
            "unit": "조원",
            "min": -20,
            "max": 10,
            "danger_low": -10,
            "danger_high": -2,
            "reverse": False,
            "description": "-10조 이하: 위험"
        }
    }
    
    # 데이터 수집
    raw_data = {
        "exchange_rate": get_exchange_rate(),
        "bond_rate_3y": get_bond_rate_3y(),
        "available_fx_ratio": get_available_fx_ratio(),
        "fx_to_gdp_ratio": get_fx_to_gdp_ratio(),
        "korea_us_rate_gap": get_korea_us_rate_gap(),
        "pf_delinquency": get_pf_delinquency(),
        "foreign_net_selling": get_foreign_net_selling()
    }
    
    # 지표 데이터 구성
    indicators = {}
    risk_scores = []
    
    for key, config in configs.items():
        data = raw_data[key]
        value = data["value"]
        risk_class, risk_text = calculate_risk_level(key, value, config)
        
        # 위험도 점수 (안전=1, 주의=2, 위험=3)
        risk_score = {"safe": 1, "warning": 2, "danger": 3}[risk_class]
        risk_scores.append(risk_score)
        
        indicators[key] = {
            **config,
            "value": value,
            "date": data["date"],
            "source": data["source"],
            "manual": data.get("manual", False),
            "risk_class": risk_class,
            "risk_text": risk_text
        }
    
    # 종합 위험도 계산
    avg_risk = sum(risk_scores) / len(risk_scores)
    if avg_risk >= 2.5:
        overall_risk = {"class": "danger", "text": "고위험", "score": avg_risk}
    elif avg_risk >= 1.8:
        overall_risk = {"class": "warning", "text": "중간위험", "score": avg_risk}
    else:
        overall_risk = {"class": "safe", "text": "저위험", "score": avg_risk}
    
    # 최종 데이터
    result = {
        "updated_at": datetime.now().isoformat(),
        "updated_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "overall_risk": overall_risk,
        "indicators": indicators
    }
    
    return result


def save_data(data):
    """데이터 JSON 파일로 저장"""
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"데이터 저장 완료: {DATA_PATH}")


def main():
    """메인 실행"""
    print("=" * 50)
    print("한국 경제 위기 지수 - 데이터 수집")
    print("=" * 50)
    print(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 데이터 수집
    data = fetch_all_indicators()
    
    # 결과 출력
    print(f"종합 위험도: {data['overall_risk']['text']}")
    print("-" * 50)
    
    for key, ind in data["indicators"].items():
        status = {"safe": "✅", "warning": "⚠️", "danger": "🔴"}[ind["risk_class"]]
        manual = "(수동)" if ind.get("manual") else "(자동)"
        print(f"{status} {ind['name']}: {ind['value']}{ind['unit']} [{ind['risk_text']}] {manual}")
    
    print("-" * 50)
    
    # 저장
    save_data(data)
    
    print("\n완료!")


if __name__ == "__main__":
    main()
