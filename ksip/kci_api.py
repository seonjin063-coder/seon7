import os
import time
import hashlib
import requests
import xml.etree.ElementTree as ET
from urllib.parse import urlencode
from dotenv import load_dotenv

BASE_URL = "https://open.kci.go.kr/po/openapi/openApiSearch.kci"
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "cache")

def load_api_key():
    load_dotenv()
    key = os.getenv("KCI_OPEN_API_KEY")
    if not key:
        # Fallback to KCI_OpenAPI_Key.txt if it exists
        txt_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "KCI_OpenAPI_Key.txt")
        if os.path.exists(txt_path):
            with open(txt_path, 'r', encoding='utf-8') as f:
                key = f.read().strip()
    if not key:
        raise ValueError("API Key not found in .env or KCI_OpenAPI_Key.txt")
    return key

def call(apiCode, **params):
    key = load_api_key()
    params["apiCode"] = apiCode
    params["key"] = key
    
    # 캐시 키 생성: apiCode와 파라미터(key 제외)를 정렬하여 해시
    cache_params = {k: v for k, v in params.items() if k != 'key'}
    cache_key_str = urlencode(sorted(cache_params.items()))
    cache_hash = hashlib.md5(cache_key_str.encode('utf-8')).hexdigest()
    
    # 캐시 디렉토리 설정
    specific_cache_dir = os.path.join(CACHE_DIR, apiCode)
    os.makedirs(specific_cache_dir, exist_ok=True)
    
    # 식별하기 쉬운 파일명 생성 (ID가 있는 경우 ID 사용)
    ident = params.get('id') or params.get('sereId') or params.get('artiId') or cache_hash
    cache_file = os.path.join(specific_cache_dir, f"{ident}.xml")
    
    if os.path.exists(cache_file):
        with open(cache_file, 'r', encoding='utf-8') as f:
            # print(f"[Cache HIT] {apiCode} - {ident}")
            return f.read()
            
    print(f"[API CALL] {apiCode} - {ident}")
    time.sleep(0.5) # Rate limiting (0.5s)
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.get(BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            xml_data = response.text
            
            # 유효한 XML인지 확인
            parse_xml(xml_data)
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                f.write(xml_data)
            return xml_data
            
        except Exception as e:
            print(f"  - Attempt {attempt+1} failed: {e}")
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt) # Exponential backoff

def parse_xml(xml_string):
    return ET.fromstring(xml_string)

def get_citation_detail(sereId):
    xml_data = call("citationDetail", id=sereId)
    return parse_xml(xml_data)

def get_reference_search(artiId):
    # KCI API에서 referenceSearch가 존재한다면 apiCode를 맞춰서 호출
    xml_data = call("referenceSearch", id=artiId) 
    return parse_xml(xml_data)

def get_article_detail(artiId):
    xml_data = call("articleDetail", id=artiId)
    return parse_xml(xml_data)

def get_article_search(**criteria):
    xml_data = call("articleSearch", **criteria)
    return parse_xml(xml_data)

def smoke_test():
    print("=== Phase 0: Smoke Test ===")
    
    print("\n1. citationDetail (sereId=001529) 테스트")
    try:
        root = get_citation_detail("001529")
        title_elem = root.find('.//journalInfo/journal-kor-name')
        title = title_elem.text if title_elem is not None else "Unknown"
        print(f"성공! 학술지명: {title}")
    except Exception as e:
        print(f"실패: {e}")
        
    print("\n2. articleDetail (ART002870171) 테스트")
    try:
        root = get_article_detail("ART002870171")
        title_elem = root.find('.//article-title[@lang="original"]')
        title = title_elem.text if title_elem is not None else "Unknown"
        print(f"성공! 논문명: {title}")
    except Exception as e:
        print(f"실패: {e}")

if __name__ == "__main__":
    smoke_test()
