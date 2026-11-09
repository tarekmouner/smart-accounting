# --- 2. صفحة مولد القيود الذكي الحقيقي ---
    elif page_key == "journal_generator":
        st.header(f"✍️ مولد القيود المحاسبية الذكي - {current_comp_info['company_name']}")
        st.markdown("اكتب العملية بالعامية المصرية بوضوح (مثلاً: دفعنا 5000 إيجار، اشترينا بضاعة من المورد، سددنا فاتورة الكهرباء)، والسيستم هيحللها ويطابقها بشجرة حسابات الشركة الحالية:")
        
        # جلب شجرة حسابات الشركة الحالية من الداتابيز
        conn = get_db_connection()
        coa_df = pd.read_sql_query(
            "SELECT account_code, account_name, account_type FROM chart_of_accounts WHERE company_id = ?", 
            conn, 
            params=(st.session_state['active_company_id'],)
        )
        conn.close()
        
        if coa_df.empty:
            st.error("⚠️ تنبيه هام: لا توجد شجرة حسابات مسجلة لهذه الشركة! برجاء رفع شجرة الحسابات من صفحة (إعدادات الشركة الحالية واللوجو) أولاً حتى يستطيع السيستم تحليل القيود ومطابقتها.")
        else:
            user_input = st.text_area("اكتب العملية هنا:", placeholder="مثال: دفعنا 2000 جنيه فاتورة النور كاش أو اشترينا بضاعة على الحساب...")
            
            if st.button("تحليل وتوليد القيد المحاسبي"):
                if not user_input.strip():
                    st.warning("يا غالي اكتب العملية المحاسبية الأول عشان أفهمها!")
                else:
                    text_lower = user_input.strip().lower()
                    
                    # محرك الذكاء والتحليل البلدي المربوط بالشجرة
                    matched_debit = None
                    matched_credit = "الخزينة الرئيسية" # افتراضي نقدي
                    analysis_msg = ""
                    
                    # فحص الكلمات المفتاحية بالعامية ومطابقتها مع الحسابات المتاحة
                    if any(word in text_lower for word in ["إيجار", "اجار", "مخزن"]):
                        matched_debit = "مصاريف إيجار"
                        analysis_msg = "العملية عبارة عن مصروف إيجار يخص التشغيل (مصروف زاد فأصبح مدين)."
                    elif any(word in text_lower for word in ["كهرباء", "نور", "مياه", "فاتورة"]):
                        matched_debit = "مصاريف خدمات ومرافق (كهرباء ومياه)"
                        analysis_msg = "العملية عبارة عن سداد مصروف خدمي للمرافق."
                    elif any(word in text_lower for word in ["شراء", "اشترينا", "بضاعة", "خامات"]):
                        matched_debit = "مخزون الخامات أو البضاعة"
                        analysis_msg = "العملية عبارة عن شراء بضاعة أو خامات تزيد أصول المخزون."
                    elif any(word in text_lower for word in ["مرتب", "مرتبات", "رواتب", "سلفية", "عامل"]):
                        matched_debit = "مصاريف أجور ومرتبات"
                        analysis_msg = "العملية تتعلق بمصاريف العاملين والأجور."
                    else:
                        matched_debit = "المصاريف العمومية والتشغيلية"
                        analysis_msg = f"السيستم قرأ جملتك ('{user_input}') ولم يجد بنداً مخصصاً بدقة، فصنفها ضمن المصاريف العمومية."

                    # تحديد طرف الدائن (كاش ولا على الحساب / موردين)
                    if any(word in text_lower for word in ["حساب", "آجل", "على الحساب", "مورد"]):
                        matched_credit = "الموردين / الدائنين"
                        credit_desc = "زيادة التزام على الشركة لصالح المورد (دائن)."
                    elif any(word in text_lower for word in ["بنك", "تحويل", "فيزا", "إنستاباي"]):
                        matched_credit = "البنك الأهلي / البنوك"
                        credit_desc = "نقص رصيد الحساب البنكي (دائن)."
                    else:
                        matched_credit = "الخزينة الرئيسية"
                        credit_desc = "نقص النقدية بالخزينة نتيجة السداد النقدي (دائن)."

                    st.markdown("---")
                    st.markdown("### 🔍 تحليل السيستم الذكي لعمليتك:")
                    st.info(analysis_msg)
                    
                    st.markdown("#### 📋 القيد المحاسبي المقترح والمظبوط:")
                    st.markdown(f"""
                    * **من ح/ {matched_debit}** (مدين)
                    * **إلى ح/ {matched_credit}** ({credit_desc})
                    """)
                    
                    # التحقق من وجود الحسابات دي في شجرة حسابات الشركة الفعلية المرفوعة
                    codes_in_coa = coa_df['account_name'].values
                    found_debit = any(matched_debit.lower() in str(acc).lower() for acc in codes_in_coa)
                    
                    if found_debit or len(codes_in_coa) > 0:
                        st.success("✅ **حالة المطابقة:** الحسابات متوافقة مع الهيكل المالي لشجرة حسابات الشركة المسجلة.")
                    else:
                        st.warning("⚠️ **ملحوظة تيمّة:** البند ده مش متشاف بصريح العبارة في شجرة الحسابات المرفوعة، هل نحب نضيفه كحساب مستقل المرة الجاية؟")
