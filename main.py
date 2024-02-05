import time
import pytz
import psycopg2
from io import StringIO
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime, timedelta


class PortalTransportador:
    def __init__(self, parameters, portal_password, db_password):
        self.settings = parameters
        self.portal_password = portal_password
        self.db_password = db_password
        self.tz = pytz.timezone(self.settings.get("LOCAL_TIMEZONE"))
        self.data = []
        self.cte_nums = None
        self.driver = None

    def initialize_driver(self):
        options = webdriver.ChromeOptions()
        self.driver = webdriver.Remote(
            command_executor=self.settings.get("REMOTE_URL"), options=options
        )
        self.driver.maximize_window()

    def login(self):
        self.driver.get(self.settings.get("LOGIN_URL"))
        login_input = WebDriverWait(
            self.driver, self.settings.get("TIMEOUT_LOADING_PAGE")
        ).until(
            EC.presence_of_element_located(
                (By.NAME, self.settings.get("LOGIN_INPUT_NAME"))
            )
        )
        password_input = self.driver.find_element(
            By.NAME, self.settings.get("PASSWORD_INPUT_NAME")
        )
        login_input.send_keys(self.settings.get("USERNAME"))
        password_input.send_keys(self.portal_password)
        ok_button = self.driver.find_element(
            By.CSS_SELECTOR, self.settings.get("LOGON_BUTTON_CSS_SELECTOR")
        )
        ok_button.click()
        option_buttion = self.driver.find_element(
            By.XPATH, self.settings.get("OPTION_BUTTON_XPATH")
        )
        option_buttion.click()

    def navigate_to_portal(self):
        self.driver.get(self.settings.get("PORTAL_URL"))

    def select_company(self):
        select = WebDriverWait(
            self.driver, self.settings.get("TIMEOUT_LOADING_PAGE")
        ).until(
            EC.presence_of_element_located(
                (By.XPATH, self.settings.get("COMPANY_SELECT_XPATH"))
            )
        )
        select.click()
        time.sleep(1.5)
        ok_button = self.driver.find_element(
            By.ID, self.settings.get("COMPANY_SELECT_BUTTON_OK_ID")
        )
        ok_button.click()

    def navigate_to_custo_frete(self):
        page_button = self.driver.find_element(
            By.ID, self.settings.get("ACOMPANHAMENTO_PAG_ID")
        )
        page_button.click()

    def navigate_to_menu(self):
        page = self.driver.find_element(
            By.ID, self.settings.get("MENU_PRINCIPAL_DIV_ID")
        )
        page.click()

    def navigate_to_ordens_page(self):
        page = self.driver.find_element(By.ID, self.settings.get("ORDENS_PAGE_DIV_ID"))
        page.click()

    def search_ctes(self):
        local_trsp_start_input = WebDriverWait(
            self.driver, self.settings.get("TIMEOUT_LOADING_PAGE")
        ).until(
            EC.presence_of_element_located(
                (By.ID, self.settings.get("LOCAL_ORG_TRSP_START_ID"))
            )
        )
        local_trsp_end_input = self.driver.find_element(
            By.ID, self.settings.get("LOCAL_ORG_TRSP_END_ID")
        )
        date_trsp_start_input = self.driver.find_element(
            By.ID, self.settings.get("DATA_TRSP_START_ID")
        )
        date_trsp_end_input = self.driver.find_element(
            By.ID, self.settings.get("DATA_TRSP_END_ID")
        )
        relatorio_button = self.driver.find_element(
            By.ID, self.settings.get("EXIBE_RELATORIO_ID")
        )
        local_trsp_start_input.send_keys(self.settings.get("LOCAL_ORG_TRSP"))
        local_trsp_end_input.send_keys(self.settings.get("LOCAL_ORG_TRSP"))
        today = datetime.now(self.tz).strftime("%d.%m.%Y")
        yesterday = datetime.now(self.tz) - timedelta(days=1)
        yesterday = yesterday.strftime("%d.%m.%Y")
        date_trsp_start_input.send_keys(yesterday)
        date_trsp_end_input.send_keys(today)
        relatorio_button.click()

    def verify_weight_coil(self, nconh):
        nconh_input = WebDriverWait(
            self.driver, self.settings.get("TIMEOUT_LOADING_PAGE")
        ).until(
            EC.presence_of_element_located((By.ID, self.settings.get("NTRSP_INPUT_ID")))
        )
        nconh_input.send_keys(nconh)

        local_trsp_input = self.driver.find_element(
            By.ID, self.settings.get("LOCAL_TRSP_ORDEM_ID")
        )
        local_trsp_input.send_keys(self.settings.get("LOCAL_ORG_TRSP"))

        exibir_button = self.driver.find_element(
            By.ID, self.settings.get("EXIBE_ORDENS_ID")
        )
        exibir_button.click()

        checkbox = WebDriverWait(
            self.driver, self.settings.get("TIMEOUT_LOADING_PAGE")
        ).until(
            EC.presence_of_element_located(
                (By.ID, self.settings.get("CHECKBOX_NCONH_ID"))
            )
        )
        checkbox.click()

        table = WebDriverWait(
            self.driver, self.settings.get("TIMEOUT_LOADING_TABLE")
        ).until(
            EC.presence_of_element_located(
                (By.XPATH, self.settings.get("TABLE_ORDENS_ID"))
            )
        )
        html_content = table.get_attribute("outerHTML")
        df = pd.read_html(StringIO(html_content))[0]
        df = df[df["Lote"].notnull()]
        max_weight = self.convert_str_to_float(df["Peso bruto"].max())
        if max_weight > 20.0:
            return True
        return False

    def get_table_result(self):
        table = WebDriverWait(
            self.driver, self.settings.get("TIMEOUT_LOADING_TABLE")
        ).until(
            EC.presence_of_element_located(
                (By.XPATH, self.settings.get("TABLE_RESULT_XPATH"))
            )
        )
        html_content = table.get_attribute("outerHTML")
        df = pd.read_html(StringIO(html_content))[0]
        df_filtered = df[df["CTRC/CT"].notnull()]
        self.df = df_filtered

    def format_data_table(self):
        self.df["NCTE"] = self.df["CTRC/CT"].apply(
            lambda x: "{:06d}".format(int(x.split("-")[0])) if pd.notnull(x) else ""
        )

    def verify_value_ctes(self):
        for cte_num in self.cte_nums:
            line = self.df.loc[self.df["NCTE"] == cte_num[0]]
            if line.empty:
                data_array = [
                    datetime.now(self.tz).strftime("%Y-%m-%d %H:%M:%S"),
                    cte_num[0],
                    cte_num[1],
                    cte_num[2],
                    cte_num[3],
                    "Não encontrado na base Vega",
                    0,
                    0,
                    0,
                    0,
                ]
                self.data.append(data_array)
            else:
                usina_value = self.convert_str_to_float(
                    line["Valor Frete Líquido"].values[0]
                ) + self.convert_str_to_float(line["Impostos"].values[0])
                usina_value = round(usina_value, 2)
                ntrsp = line["Trsp."].values[0]
                self.check_values(cte_num, usina_value, None, ntrsp)

    def convert_str_to_float(self, s):
        try:
            s = str(s)
            s = s.replace(",", "")
            s = s.replace(".", "")
            resultado = float(f"{s[:-2]}.{s[-2:]}")
            return resultado
        except ValueError:
            print("Erro: A string não está no formato adequado.")
            return None

    def check_values(self, cte_num, usina_value, msg, ntrsp):
        if msg == None:
            diff = usina_value - cte_num[4]
            diff = round(diff, 2)
            if abs(diff) >= float(self.settings.get("MAX_DIFF")):
                msg = f"Diferença de valor encontrada"
            else:
                msg = f"OK"
        else:
            diff = 0
        data_array = [
            datetime.now(self.tz).strftime("%Y-%m-%d %H:%M:%S"),
            cte_num[0],
            cte_num[1],
            cte_num[2],
            cte_num[3],
            msg,
            usina_value,
            cte_num[4],
            diff,
            ntrsp,
        ]
        self.data.append(data_array)

    def connect_to_postgres(self):
        conn = psycopg2.connect(
            host=self.settings.get("DB_HOST"),
            database=self.settings.get("DB_NAME"),
            user=self.settings.get("DB_USER"),
            password=self.db_password,
        )
        self.conn = conn

    def get_cte_tg99(self):
        cursor = None
        try:
            today = datetime.now(tz=self.tz)
            limit_date = (today - timedelta(days=1)).strftime("%Y-%m-%d")
            cursor = self.conn.cursor()
            cursor.execute(self.settings.get("SQL_SELECT_QUERY").format(limit_date))
            rows = cursor.fetchall()
            sorted_list = sorted(rows, key=lambda x: int(x[0]), reverse=True)
            formatted_data_list = [
                (a, b, c, d.strftime("%Y-%m-%d"), e) for a, b, c, d, e in sorted_list
            ]
            self.cte_nums = formatted_data_list
            return formatted_data_list

        finally:
            if cursor:
                cursor.close()

    def close_driver(self):
        if self.driver:
            self.driver.quit()
