import streamlit as st
from supabase import create_client, Client

# Supabase 설정
SUPABASE_URL = "https://cqwiugtbezctaukzmxnj.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNxd2l1Z3RiZXpjdGF1a3pteG5qIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDExODY3ODMsImV4cCI6MjA1Njc2Mjc4M30.DV6ruUw4VBSfbfZD3VrXPAPCNIEu430RHm5dUDOGMbo"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 상태 옵션
CONDITION_OPTIONS = ["상", "중", "하"]

# 데이터 가져오기 함수
def get_brands():
    return supabase.table("brands").select("id, brand_name").execute().data

def get_partgroup1():
    return supabase.table("part_groups").select("id, group_name").eq("parent_id", None).execute().data

def get_partgroup2(partgroup1_id):
    return supabase.table("part_groups").select("id, group_name").eq("parent_id", partgroup1_id).execute().data

# 검색 기능
def search_data(table, search_term):
    response = supabase.table(table).select("*").or_(
        f"product_name.ilike.%{search_term}%,product_code.ilike.%{search_term}%,genuine_code.ilike.%{search_term}%,compatible_code.ilike.%{search_term}%"
    ).execute()
    return response.data

# 상품 관리 화면
def product_management():
    st.subheader("상품 관리")
    
    tab1, tab2, tab3 = st.tabs(["등록", "업데이트/삭제", "검색"])
    
    # 등록
    with tab1:
        with st.form("product_form"):
            # 브랜드 선택
            brands = get_brands()
            brand_name = st.selectbox("브랜드", [b["brand_name"] for b in brands])
            brand_id = next(b["id"] for b in brands if b["brand_name"] == brand_name)
            
            # partgroup1 선택
            partgroup1_list = get_partgroup1()
            partgroup1_name = st.selectbox("부품 그룹 1", [pg["group_name"] for pg in partgroup1_list])
            partgroup1_id = next(pg["id"] for pg in partgroup1_list if pg["group_name"] == partgroup1_name)
            
            # partgroup2 선택 (partgroup1에 따라 필터링)
            partgroup2_list = get_partgroup2(partgroup1_id)
            partgroup2_name = st.selectbox("부품 그룹 2", [pg["group_name"] for pg in partgroup2_list])
            partgroup2_id = next(pg["id"] for pg in partgroup2_list if pg["group_name"] == partgroup2_name)
            
            product_name = st.text_input("제품명")
            product_code = st.text_input("제품번호")
            genuine_code = st.text_input("정품번호")
            compatible_code = st.text_input("호환번호")
            remarks = st.text_area("비고")
            condition = st.selectbox("상태", CONDITION_OPTIONS)
            image_url = st.text_input("이미지 URL")
            submit = st.form_submit_button("등록")
            
            if submit:
                data = {
                    "product_name": product_name,
                    "product_code": product_code,
                    "genuine_code": genuine_code,
                    "compatible_code": compatible_code,
                    "brand_id": brand_id,
                    "partgroup2_id": partgroup2_id,
                    "remarks": remarks,
                    "condition": condition,
                    "image_url": image_url
                }
                supabase.table("products").insert(data).execute()
                st.success("상품이 등록되었습니다!")
    
    # 업데이트/삭제
    with tab2:
        products = supabase.table("products").select("*, brands(brand_name), part_groups(group_name)").execute().data
        selected_product = st.selectbox("수정/삭제할 상품 선택", [p["product_name"] for p in products])
        product_data = next((p for p in products if p["product_name"] == selected_product), None)
        
        if product_data:
            with st.form("update_product_form"):
                brands = get_brands()
                brand_name = st.selectbox("브랜드", [b["brand_name"] for b in brands], 
                                        index=[b["brand_name"] for b in brands].index(product_data["brands"]["brand_name"]))
                brand_id = next(b["id"] for b in brands if b["brand_name"] == brand_name)
                
                partgroup1_list = get_partgroup1()
                partgroup1_name = st.selectbox("부품 그룹 1", [pg["group_name"] for pg in partgroup1_list])
                partgroup1_id = next(pg["id"] for pg in partgroup1_list if pg["group_name"] == partgroup1_name)
                
                partgroup2_list = get_partgroup2(partgroup1_id)
                partgroup2_name = st.selectbox("부품 그룹 2", [pg["group_name"] for pg in partgroup2_list], 
                                             index=[pg["group_name"] for pg in partgroup2_list].index(product_data["part_groups"]["group_name"]))
                partgroup2_id = next(pg["id"] for pg in partgroup2_list if pg["group_name"] == partgroup2_name)
                
                product_name = st.text_input("제품명", product_data["product_name"])
                product_code = st.text_input("제품번호", product_data["product_code"])
                genuine_code = st.text_input("정품번호", product_data["genuine_code"])
                compatible_code = st.text_input("호환번호", product_data["compatible_code"])
                remarks = st.text_area("비고", product_data["remarks"])
                condition = st.selectbox("상태", CONDITION_OPTIONS, index=CONDITION_OPTIONS.index(product_data["condition"]))
                image_url = st.text_input("이미지 URL", product_data["image_url"])
                update = st.form_submit_button("업데이트")
                delete = st.form_submit_button("삭제")
                
                if update:
                    data = {
                        "product_name": product_name,
                        "product_code": product_code,
                        "genuine_code": genuine_code,
                        "compatible_code": compatible_code,
                        "brand_id": brand_id,
                        "partgroup2_id": partgroup2_id,
                        "remarks": remarks,
                        "condition": condition,
                        "image_url": image_url
                    }
                    supabase.table("products").update(data).eq("id", product_data["id"]).execute()
                    st.success("상품이 업데이트되었습니다!")
                if delete:
                    supabase.table("products").delete().eq("id", product_data["id"]).execute()
                    st.success("상품이 삭제되었습니다!")
    
    # 검색
    with tab3:
        search_term = st.text_input("검색어 입력 (제품명/제품번호/정품번호/호환번호)")
        if search_term:
            results = search_data("products", search_term)
            st.table(results)

# 재고 관리 화면 (변경 없음, 이전 코드 재사용)
def stock_management():
    st.subheader("재고 관리")
    
    tab1, tab2, tab3 = st.tabs(["등록", "업데이트/삭제", "검색"])
    
    with tab1:
        products = supabase.table("products").select("id, product_name").execute().data
        with st.form("stock_form"):
            product = st.selectbox("상품 선택", [p["product_name"] for p in products])
            product_id = next(p["id"] for p in products if p["product_name"] == product)
            quantity = st.number_input("수량", min_value=0)
            remarks = st.text_area("비고")
            condition = st.selectbox("상태", CONDITION_OPTIONS)
            image_url = st.text_input("이미지 URL")
            submit = st.form_submit_button("등록")
            
            if submit:
                data = {
                    "product_id": product_id,
                    "quantity": quantity,
                    "remarks": remarks,
                    "condition": condition,
                    "image_url": image_url
                }
                supabase.table("stock").insert(data).execute()
                st.success("재고가 등록되었습니다!")
    
    with tab2:
        stock_items = supabase.table("stock").select("*").execute().data
        selected_stock = st.selectbox("수정/삭제할 재고 선택", [f"{s['id']} - {s['quantity']}" for s in stock_items])
        stock_data = next((s for s in stock_items if f"{s['id']} - {s['quantity']}" == selected_stock), None)
        
        if stock_data:
            with st.form("update_stock_form"):
                products = supabase.table("products").select("id, product_name").execute().data
                product = st.selectbox("상품 선택", [p["product_name"] for p in products], 
                                     index=[p["id"] for p in products].index(stock_data["product_id"]))
                quantity = st.number_input("수량", min_value=0, value=stock_data["quantity"])
                remarks = st.text_area("비고", stock_data["remarks"])
                condition = st.selectbox("상태", CONDITION_OPTIONS, index=CONDITION_OPTIONS.index(stock_data["condition"]))
                image_url = st.text_input("이미지 URL", stock_data["image_url"])
                update = st.form_submit_button("업데이트")
                delete = st.form_submit_button("삭제")
                
                if update:
                    data = {
                        "product_id": next(p["id"] for p in products if p["product_name"] == product),
                        "quantity": quantity,
                        "remarks": remarks,
                        "condition": condition,
                        "image_url": image_url
                    }
                    supabase.table("stock").update(data).eq("id", stock_data["id"]).execute()
                    st.success("재고가 업데이트되었습니다!")
                if delete:
                    supabase.table("stock").delete().eq("id", stock_data["id"]).execute()
                    st.success("재고가 삭제되었습니다!")
    
    with tab3:
        search_term = st.text_input("검색어 입력 (제품명/제품번호/정품번호/호환번호)")
        if search_term:
            results = supabase.table("stock").select("*, products(product_name, product_code, genuine_code, compatible_code)").execute().data
            filtered = [r for r in results if search_term.lower() in str(r["products"]).lower()]
            st.table(filtered)

# 메인 앱
def main():
    st.title("재고 관리 앱")
    menu = st.sidebar.selectbox("메뉴", ["상품 관리", "재고 관리"])
    
    if menu == "상품 관리":
        product_management()
    elif menu == "재고 관리":
        stock_management()

if __name__ == "__main__":
    main()
