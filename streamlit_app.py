import streamlit as st
import os
from supabase import create_client, Client
import logging
from typing import List, Dict, Any, Optional, Tuple

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Supabase 설정: Streamlit Cloud의 secrets.toml에서 로드
SUPABASE_URL = os.getenv("SUPABASE_URL")  # secrets.toml에서 제공
SUPABASE_KEY = os.getenv("SUPABASE_KEY")  # secrets.toml에서 제공

# 상태 옵션
CONDITION_OPTIONS = ["상", "중", "하"]

# 데이터베이스 클라이언트 초기화 함수
def initialize_db_client() -> Optional[Client]:
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("Supabase URL 또는 Key가 설정되지 않았습니다.")
        st.error("환경 변수가 누락되었습니다. 관리자에게 문의하세요.")
        return None
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        test_result = supabase.table("brands").select("id").limit(1).execute()
        logger.info("데이터베이스 연결 성공")
        return supabase
    except Exception as e:
        logger.error(f"데이터베이스 연결 실패: {str(e)}")
        st.error("데이터베이스 연결에 실패했습니다.")
        return None

# 데이터 가져오기 함수
def get_data(supabase: Client, table: str, columns: str = "*", filters: Dict = None) -> List[Dict]:
    try:
        query = supabase.table(table).select(columns)
        if filters:
            for key, value in filters.items():
                if value is not None:
                    query = query.eq(key, value)
        response = query.execute()
        return response.data
    except Exception as e:
        logger.error(f"{table} 데이터 조회 실패: {str(e)}")
        return []

def get_brands(supabase: Client) -> List[Dict]:
    return get_data(supabase, "brands", "id, brand_name")

def get_partgroup1(supabase: Client) -> List[Dict]:
    return get_data(supabase, "part_groups", "id, group_name", {"parent_id": None})

def get_partgroup2(supabase: Client, partgroup1_id: int) -> List[Dict]:
    return get_data(supabase, "part_groups", "id, group_name", {"parent_id": partgroup1_id})

# 검색 기능
def search_data(supabase: Client, table: str, search_term: str) -> List[Dict]:
    try:
        search_term = search_term.strip().lower()
        if not search_term:
            return []
        response = supabase.table(table).select("*").or_(
            f"product_name.ilike.%{search_term}%,product_code.ilike.%{search_term}%,"
            f"genuine_code.ilike.%{search_term}%,compatible_code.ilike.%{search_term}%"
        ).execute()
        return response.data
    except Exception as e:
        logger.error(f"검색 실패: {str(e)}")
        return []

def search_partgroup(supabase: Client, search_term: str, is_group1: bool = True) -> List[Dict]:
    try:
        search_term = search_term.strip().lower()
        if not search_term:
            return []
        query = supabase.table("part_groups").select("id, group_name, parent_id").ilike("group_name", f"%{search_term}%")
        if is_group1:
            query = query.is_("parent_id", None)
        else:
            query = query.not_.is_("parent_id", None)
        response = query.execute()
        return response.data
    except Exception as e:
        logger.error(f"부품 그룹 검색 실패: {str(e)}")
        return []

# 데이터베이스 작업 함수
def insert_data(supabase: Client, table: str, data: Dict) -> bool:
    try:
        result = supabase.table(table).insert(data).execute()
        return bool(result.data)
    except Exception as e:
        logger.error(f"{table} 데이터 삽입 실패: {str(e)}")
        return False

def update_data(supabase: Client, table: str, data: Dict, id: int) -> bool:
    try:
        result = supabase.table(table).update(data).eq("id", id).execute()
        return bool(result.data)
    except Exception as e:
        logger.error(f"{table} ID {id} 데이터 업데이트 실패: {str(e)}")
        return False

def delete_data(supabase: Client, table: str, id: int) -> bool:
    try:
        result = supabase.table(table).delete().eq("id", id).execute()
        return bool(result.data)
    except Exception as e:
        logger.error(f"{table} ID {id} 데이터 삭제 실패: {str(e)}")
        return False

# 데이터 검증 함수
def validate_product_data(data: Dict) -> Tuple[bool, str]:
    if not data["product_name"]:
        return False, "제품명을 입력해주세요."
    if not data["product_code"]:
        return False, "제품번호를 입력해주세요."
    return True, ""

def validate_stock_data(data: Dict) -> Tuple[bool, str]:
    if data["quantity"] < 0:
        return False, "수량은 0 이상이어야 합니다."
    return True, ""

# 상태 초기화
if "supabase" not in st.session_state:
    st.session_state.supabase = initialize_db_client()
if "messages" not in st.session_state:
    st.session_state.messages = []

# 상품 관리 화면
def product_management(supabase: Client):
    st.subheader("상품 관리")
    tab1, tab2, tab3 = st.tabs(["등록", "업데이트/삭제", "검색"])

    with tab1:
        with st.form("product_form"):
            brands = get_brands(supabase)
            brand_id = None
            if brands:
                brand_name = st.selectbox("브랜드", [b["brand_name"] for b in brands])
                brand_id = next((b["id"] for b in brands if b["brand_name"] == brand_name), None)
            else:
                st.warning("등록된 브랜드가 없습니다.")

            partgroup1_list = get_partgroup1(supabase)
            partgroup2_id = None
            if partgroup1_list:
                partgroup1_name = st.selectbox("부품 그룹 1", [pg["group_name"] for pg in partgroup1_list])
                partgroup1_id = next((pg["id"] for pg in partgroup1_list if pg["group_name"] == partgroup1_name), None)
                partgroup2_list = get_partgroup2(supabase, partgroup1_id)
                if partgroup2_list:
                    partgroup2_name = st.selectbox("부품 그룹 2", [pg["group_name"] for pg in partgroup2_list])
                    partgroup2_id = next((pg["id"] for pg in partgroup2_list if pg["group_name"] == partgroup2_name), None)
                else:
                    st.warning("부품 그룹 2가 없습니다.")
            else:
                st.warning("부품 그룹 1이 없습니다.")

            product_name = st.text_input("제품명")
            product_code = st.text_input("제품번호")
            genuine_code = st.text_input("정품번호")
            compatible_code = st.text_input("호환번호")
            remarks = st.text_area("비고")
            condition = st.selectbox("상태", CONDITION_OPTIONS)
            image_url = st.text_input("이미지 URL")
            submit = st.form_submit_button("등록", disabled=not (brand_id and partgroup2_id))

            if submit:
                try:
                    data = {
                        "product_name": product_name, "product_code": product_code,
                        "genuine_code": genuine_code, "compatible_code": compatible_code,
                        "brand_id": brand_id, "partgroup2_id": partgroup2_id,
                        "remarks": remarks, "condition": condition, "image_url": image_url
                    }
                    is_valid, error_msg = validate_product_data(data)
                    if is_valid and insert_data(supabase, "products", data):
                        st.session_state.messages.append("상품이 성공적으로 등록되었습니다!")
                    else:
                        st.session_state.messages.append(error_msg)
                except Exception as e:
                    st.session_state.messages.append(f"등록 실패: {str(e)}")

    with tab2:
        try:
            products = get_data(supabase, "products", "*, brands(brand_name), part_groups(group_name)")
            if products:
                selected_product = st.selectbox("상품 선택", [p["product_name"] for p in products])
                product_data = next((p for p in products if p["product_name"] == selected_product), None)
                if product_data:
                    with st.form("update_product_form"):
                        brands = get_brands(supabase)
                        brand_name = st.selectbox("브랜드", [b["brand_name"] for b in brands],
                                                  index=[b["brand_name"] for b in brands].index(product_data["brands"]["brand_name"]))
                        brand_id = next((b["id"] for b in brands if b["brand_name"] == brand_name), None)

                        partgroup1_list = get_partgroup1(supabase)
                        partgroup1_name = st.selectbox("부품 그룹 1", [pg["group_name"] for pg in partgroup1_list])
                        partgroup1_id = next((pg["id"] for pg in partgroup1_list if pg["group_name"] == partgroup1_name), None)
                        partgroup2_list = get_partgroup2(supabase, partgroup1_id)
                        partgroup2_name = st.selectbox("부품 그룹 2", [pg["group_name"] for pg in partgroup2_list],
                                                       index=[pg["group_name"] for pg in partgroup2_list].index(product_data["part_groups"]["group_name"]))
                        partgroup2_id = next((pg["id"] for pg in partgroup2_list if pg["group_name"] == partgroup2_name), None)

                        product_name = st.text_input("제품명", product_data["product_name"])
                        product_code = st.text_input("제품번호", product_data["product_code"])
                        genuine_code = st.text_input("정품번호", product_data["genuine_code"])
                        compatible_code = st.text_input("호환번호", product_data["compatible_code"])
                        remarks = st.text_area("비고", product_data["remarks"])
                        condition = st.selectbox("상태", CONDITION_OPTIONS, index=CONDITION_OPTIONS.index(product_data["condition"]))
                        image_url = st.text_input("이미지 URL", product_data["image_url"])
                        col1, col2 = st.columns(2)
                        with col1:
                            update = st.form_submit_button("업데이트")
                        with col2:
                            delete = st.form_submit_button("삭제")

                        if update:
                            data = {
                                "product_name": product_name, "product_code": product_code,
                                "genuine_code": genuine_code, "compatible_code": compatible_code,
                                "brand_id": brand_id, "partgroup2_id": partgroup2_id,
                                "remarks": remarks, "condition": condition, "image_url": image_url
                            }
                            is_valid, error_msg = validate_product_data(data)
                            if is_valid and update_data(supabase, "products", data, product_data["id"]):
                                st.session_state.messages.append("상품이 성공적으로 업데이트되었습니다!")
                            else:
                                st.session_state.messages.append(error_msg)
                        if delete:
                            if get_data(supabase, "stock", "*", {"product_id": product_data["id"]}):
                                st.session_state.messages.append("연결된 재고가 있어 삭제할 수 없습니다.")
                            elif delete_data(supabase, "products", product_data["id"]):
                                st.session_state.messages.append("상품이 성공적으로 삭제되었습니다!")
            else:
                st.warning("등록된 상품이 없습니다.")
        except Exception as e:
            st.session_state.messages.append(f"업데이트/삭제 오류: {str(e)}")

    with tab3:
        search_term = st.text_input("검색어 입력")
        if search_term:
            try:
                results = search_data(supabase, "products", search_term)
                if results:
                    brands = {b["id"]: b["brand_name"] for b in get_brands(supabase)}
                    display_data = [{"product_name": r["product_name"], "product_code": r["product_code"],
                                     "brand": brands.get(r["brand_id"], "알 수 없음"), "condition": r["condition"]} for r in results]
                    st.dataframe(display_data)
                    st.session_state.messages.append(f"총 {len(results)}개의 결과가 검색되었습니다.")
                else:
                    st.session_state.messages.append("검색 결과가 없습니다.")
            except Exception as e:
                st.session_state.messages.append(f"검색 오류: {str(e)}")

# 재고 관리 화면
def stock_management(supabase: Client):
    st.subheader("재고 관리")
    tab1, tab2, tab3 = st.tabs(["등록", "업데이트/삭제", "검색"])

    with tab1:
        try:
            products = get_data(supabase, "products", "id, product_name, product_code")
            if products:
                with st.form("stock_form"):
                    product_labels = [f"{p['product_name']} ({p['product_code']})" for p in products]
                    product_label = st.selectbox("상품 선택", product_labels)
                    product_id = products[product_labels.index(product_label)]["id"]
                    quantity = st.number_input("수량", min_value=0, value=1)
                    remarks = st.text_area("비고")
                    condition = st.selectbox("상태", CONDITION_OPTIONS)
                    image_url = st.text_input("이미지 URL")
                    submit = st.form_submit_button("등록")

                    if submit:
                        data = {"product_id": product_id, "quantity": quantity, "remarks": remarks,
                                "condition": condition, "image_url": image_url}
                        is_valid, error_msg = validate_stock_data(data)
                        if is_valid and insert_data(supabase, "stock", data):
                            st.session_state.messages.append("재고가 성공적으로 등록되었습니다!")
                        else:
                            st.session_state.messages.append(error_msg)
            else:
                st.warning("등록된 상품이 없습니다.")
        except Exception as e:
            st.session_state.messages.append(f"재고 등록 오류: {str(e)}")

    with tab2:
        try:
            stock_items = supabase.table("stock").select("*, products(product_name, product_code)").execute().data
            if stock_items:
                stock_labels = [f"ID: {s['id']} - {s['products']['product_name']} ({s['products']['product_code']})" for s in stock_items]
                selected_stock = st.selectbox("재고 선택", stock_labels)
                stock_data = stock_items[stock_labels.index(selected_stock)]
                with st.form("update_stock_form"):
                    products = get_data(supabase, "products", "id, product_name, product_code")
                    product_labels = [f"{p['product_name']} ({p['product_code']})" for p in products]
                    product_label = st.selectbox("상품 선택", product_labels,
                                                 index=product_labels.index(f"{stock_data['products']['product_name']} ({stock_data['products']['product_code']})"))
                    product_id = products[product_labels.index(product_label)]["id"]
                    quantity = st.number_input("수량", min_value=0, value=stock_data["quantity"])
                    remarks = st.text_area("비고", stock_data["remarks"] or "")
                    condition = st.selectbox("상태", CONDITION_OPTIONS, index=CONDITION_OPTIONS.index(stock_data["condition"]))
                    image_url = st.text_input("이미지 URL", stock_data["image_url"] or "")
                    col1, col2 = st.columns(2)
                    with col1:
                        update = st.form_submit_button("업데이트")
                    with col2:
                        delete = st.form_submit_button("삭제")

                    if update:
                        data = {"product_id": product_id, "quantity": quantity, "remarks": remarks,
                                "condition": condition, "image_url": image_url}
                        is_valid, error_msg = validate_stock_data(data)
                        if is_valid and update_data(supabase, "stock", data, stock_data["id"]):
                            st.session_state.messages.append("재고가 성공적으로 업데이트되었습니다!")
                        else:
                            st.session_state.messages.append(error_msg)
                    if delete and delete_data(supabase, "stock", stock_data["id"]):
                        st.session_state.messages.append("재고가 성공적으로 삭제되었습니다!")
            else:
                st.warning("등록된 재고가 없습니다.")
        except Exception as e:
            st.session_state.messages.append(f"재고 업데이트/삭제 오류: {str(e)}")

    with tab3:
        search_term = st.text_input("검색어 입력")
        if search_term:
            try:
                product_results = search_data(supabase, "products", search_term)
                if product_results:
                    product_ids = [p["id"] for p in product_results]
                    stock_results = [s for pid in product_ids for s in get_data(supabase, "stock", "*", {"product_id": pid})]
                    if stock_results:
                        product_dict = {p["id"]: p for p in product_results}
                        display_data = [{"재고 ID": s["id"], "제품명": product_dict[s["product_id"]]["product_name"],
                                         "수량": s["quantity"], "상태": s["condition"]} for s in stock_results]
                        st.dataframe(display_data)
                        st.session_state.messages.append(f"총 {len(stock_results)}개의 재고가 검색되었습니다.")
                    else:
                        st.session_state.messages.append("재고 정보가 없습니다.")
                else:
                    st.session_state.messages.append("검색 결과가 없습니다.")
            except Exception as e:
                st.session_state.messages.append(f"재고 검색 오류: {str(e)}")

# 브랜드 관리 화면
def brand_management(supabase: Client):
    st.subheader("브랜드 관리")
    col1, col2 = st.columns(2)

    with col1:
        with st.form("add_brand_form"):
            brand_name = st.text_input("브랜드 이름")
            submit = st.form_submit_button("추가")
            if submit:
                try:
                    if brand_name and insert_data(supabase, "brands", {"brand_name": brand_name}):
                        st.session_state.messages.append(f"브랜드 '{brand_name}'이 추가되었습니다!")
                    else:
                        st.session_state.messages.append("브랜드 이름을 입력해주세요.")
                except Exception as e:
                    st.session_state.messages.append(f"브랜드 추가 오류: {str(e)}")

    with col2:
        brands = get_brands(supabase)
        if brands:
            for brand in brands:
                col_info, col_delete = st.columns([3, 1])
                with col_info:
                    st.write(f"{brand['id']}: {brand['brand_name']}")
                with col_delete:
                    if st.button("삭제", key=f"delete_brand_{brand['id']}"):
                        try:
                            products = get_data(supabase, "products", "*", {"brand_id": brand['id']})
                            if products:
                                st.session_state.messages.append(f"연결된 상품이 {len(products)}개 있어 삭제할 수 없습니다.")
                            elif delete_data(supabase, "brands", brand['id']):
                                st.session_state.messages.append(f"브랜드 '{brand['brand_name']}'이 삭제되었습니다!")
                        except Exception as e:
                            st.session_state.messages.append(f"브랜드 삭제 오류: {str(e)}")
        else:
            st.info("등록된 브랜드가 없습니다.")

# 부품 그룹 관리 화면
def partgroup_management(supabase: Client):
    st.subheader("부품 그룹 관리")
    tab1, tab2, tab3 = st.tabs(["그룹 1 관리", "그룹 2 관리", "검색"])

    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            with st.form("add_group1_form"):
                group_name = st.text_input("그룹 이름")
                submit = st.form_submit_button("추가")
                if submit:
                    try:
                        if group_name and insert_data(supabase, "part_groups", {"group_name": group_name, "parent_id": None}):
                            st.session_state.messages.append(f"부품 그룹 1 '{group_name}'이 추가되었습니다!")
                        else:
                            st.session_state.messages.append("그룹 이름을 입력해주세요.")
                    except Exception as e:
                        st.session_state.messages.append(f"그룹 1 추가 오류: {str(e)}")

        with col2:
            group1_list = get_partgroup1(supabase)
            if group1_list:
                for group in group1_list:
                    col_info, col_delete = st.columns([3, 1])
                    with col_info:
                        st.write(f"{group['id']}: {group['group_name']}")
                    with col_delete:
                        if st.button("삭제", key=f"delete_group1_{group['id']}"):
                            try:
                                subgroup = get_data(supabase, "part_groups", "*", {"parent_id": group['id']})
                                if subgroup:
                                    st.session_state.messages.append(f"하위 그룹이 {len(subgroup)}개 있어 삭제할 수 없습니다.")
                                elif delete_data(supabase, "part_groups", group['id']):
                                    st.session_state.messages.append(f"그룹 '{group['group_name']}'이 삭제되었습니다!")
                            except Exception as e:
                                st.session_state.messages.append(f"그룹 1 삭제 오류: {str(e)}")
            else:
                st.info("부품 그룹 1이 없습니다.")

    with tab2:
        col1, col2 = st.columns(2)
        with col1:
            with st.form("add_group2_form"):
                group1_list = get_partgroup1(supabase)
                parent_id = None
                if group1_list:
                    group1_name = st.selectbox("상위 그룹 선택", [g["group_name"] for g in group1_list])
                    parent_id = next((g["id"] for g in group1_list if g["group_name"] == group1_name), None)
                group_name = st.text_input("그룹 2 이름")
                submit = st.form_submit_button("추가", disabled=not parent_id)
                if submit:
                    try:
                        if group_name and insert_data(supabase, "part_groups", {"group_name": group_name, "parent_id": parent_id}):
                            st.session_state.messages.append(f"부품 그룹 2 '{group_name}'이 추가되었습니다!")
                        else:
                            st.session_state.messages.append("그룹 이름을 입력해주세요.")
                    except Exception as e:
                        st.session_state.messages.append(f"그룹 2 추가 오류: {str(e)}")

        with col2:
            if group1_list:
                selected_group1 = st.selectbox("상위 그룹 필터", [g["group_name"] for g in group1_list])
                selected_group1_id = next((g["id"] for g in group1_list if g["group_name"] == selected_group1), None)
                group2_list = get_partgroup2(supabase, selected_group1_id)
                if group2_list:
                    for group in group2_list:
                        col_info, col_delete = st.columns([3, 1])
                        with col_info:
                            st.write(f"{group['id']}: {group['group_name']}")
                        with col_delete:
                            if st.button("삭제", key=f"delete_group2_{group['id']}"):
                                try:
                                    products = get_data(supabase, "products", "*", {"partgroup2_id": group['id']})
                                    if products:
                                        st.session_state.messages.append(f"연결된 상품이 {len(products)}개 있어 삭제할 수 없습니다.")
                                    elif delete_data(supabase, "part_groups", group['id']):
                                        st.session_state.messages.append(f"그룹 '{group['group_name']}'이 삭제되었습니다!")
                                except Exception as e:
                                    st.session_state.messages.append(f"그룹 2 삭제 오류: {str(e)}")
                else:
                    st.info(f"'{selected_group1}'에 속한 그룹 2가 없습니다.")
            else:
                st.info("부품 그룹 1이 없습니다.")

    with tab3:
        search_term = st.text_input("그룹 검색어 입력")
        if search_term:
            try:
                group1_results = search_partgroup(supabase, search_term, True)
                group2_results = search_partgroup(supabase, search_term, False)
                if group1_results or group2_results:
                    st.write("그룹 1 결과:")
                    st.dataframe(group1_results)
                    st.write("그룹 2 결과:")
                    st.dataframe(group2_results)
                    st.session_state.messages.append(f"그룹 1: {len(group1_results)}, 그룹 2: {len(group2_results)}개 검색됨")
                else:
                    st.session_state.messages.append("검색 결과가 없습니다.")
            except Exception as e:
                st.session_state.messages.append(f"그룹 검색 오류: {str(e)}")

# 메인 앱
def main():
    st.title("재고 관리 시스템")
    supabase = st.session_state.supabase
    if supabase:
        menu = st.sidebar.selectbox("메뉴", ["상품 관리", "재고 관리", "브랜드 관리", "부품 그룹 관리"])
        if menu == "상품 관리":
            product_management(supabase)
        elif menu == "재고 관리":
            stock_management(supabase)
        elif menu == "브랜드 관리":
            brand_management(supabase)
        elif menu == "부품 그룹 관리":
            partgroup_management(supabase)

        # 메시지 표시 및 초기화
        if st.session_state.messages:
            for msg in st.session_state.messages:
                st.info(msg)
            st.session_state.messages = []

if __name__ == "__main__":
    main()
