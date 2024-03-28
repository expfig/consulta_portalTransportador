import time
from io import StringIO
from datetime import datetime, timedelta

import pandas as pd
import pytz
from botcity.maestro import *
from decouple import config
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from tools.database import Database
from tools.log_setup import get_logger
from tools.secrets import get_secret

BotMaestroSDK.RAISE_NOT_CONNECTED = False

logger = get_logger("Consulta_PortalTransportador")


class PortalTransportador:
    def __init__(self):
        """
        Inicializa a instância do bot.

        Args:
            None

        Returns:
            None
        """
        self.portal_user = get_secret(
            vault="botcity", label="consulta_PortalTransportador", key="PORTAL_USER"
        )
        self.portal_password = get_secret(
            vault="botcity", label="consulta_PortalTransportador", key="PORTAL_PASSWORD"
        )
        db_log_user = get_secret(vault="botcity", label="db_log", key="user")
        db_log_password = get_secret(vault="botcity", label="db_log", key="password")
        db_sgt20_user = get_secret(vault="botcity", label="db_sgt20", key="user")
        db_sgt20_password = get_secret(
            vault="botcity", label="db_sgt20", key="password"
        )
        db_efaccess_user = get_secret(vault="botcity", label="db_efaccess", key="user")
        db_efaccess_password = get_secret(
            vault="botcity", label="db_efaccess", key="password"
        )
        self.db_efaccess = Database(
            connection_string=config("db_efaccess_connection_string").format(
                user=db_efaccess_user, password=db_efaccess_password
            )
        )
        self.db_log = Database(
            connection_string=config("db_log_connection_string").format(
                user=db_log_user, password=db_log_password
            )
        )
        self.db_sgt20 = Database(
            connection_string=config("db_sgt20_connection_string").format(
                user=db_sgt20_user, password=db_sgt20_password
            )
        )
        self.result_data = []
        self.driver = None
        self.tz = pytz.timezone(config("timezone"))

    def get_data_ctes(self, tags, processados):
        max_date = datetime.now(self.tz) - timedelta(days=2)
        return self.db_efaccess.selection(
            config("query_get_data_vega"),
            tags=tags,
            max_date=max_date,
            processados=processados,
        )

    def get_data_processada(self):
        max_date = datetime.now(self.tz) - timedelta(days=2)
        data = self.db_log.selection(
            config("query_get_data_processada"), max_date=max_date
        )
        array_data = [i[0] for i in data]
        return array_data

    def initialize_driver(self):
        options = webdriver.ChromeOptions()
        self.driver = webdriver.Remote(
            command_executor=config("selenium_remote_url"), options=options
        )
        self.driver.maximize_window()

    def login(self):
        self.driver.get(config("portal_url_login_page"))
        login_input = WebDriverWait(self.driver, config("timeout_loading_page")).until(
            EC.presence_of_element_located((By.NAME, config("portal_name_login_input")))
        )
        password_input = self.driver.find_element(
            By.NAME, config("portal_name_password_input")
        )
        login_input.send_keys(self.portal_user)
        password_input.send_keys(self.portal_password)
        ok_button = self.driver.find_element(
            By.CSS_SELECTOR,
            config("portal_css_selector_login_button").replace("||", "="),
        )
        ok_button.click()
        option_buttion = self.driver.find_element(
            By.XPATH, config("portal_xpath_option_button").replace("||", "=")
        )
        option_buttion.click()

    def navigate_to_portal(self):
        self.driver.get(config("portal_url_portal_page"))

    def select_company(self, company):
        select = WebDriverWait(self.driver, config("timeout_loading_page")).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    config("portal_company_select_xpath")
                    .format(company=company)
                    .replace("||", "="),
                )
            )
        )
        select.click()
        time.sleep(1.5)
        ok_button = self.driver.find_element(
            By.ID, config("portal_company_select_button_ok_id")
        )
        ok_button.click()

    def navigate_to_custo_frete(self):
        page_button = self.driver.find_element(
            By.ID, config("portal_acompanhamento_pag_id")
        )
        page_button.click()

    def search_ctes(self):
        date_trsp_start_input = WebDriverWait(
            self.driver, config("timeout_loading_page")
        ).until(
            EC.presence_of_element_located((By.ID, config("portal_data_trsp_start_id")))
        )
        date_trsp_end_input = self.driver.find_element(
            By.ID, config("portal_data_trsp_end_id")
        )
        relatorio_button = self.driver.find_element(
            By.ID, config("portal_exibe_relatorio_id")
        )
        today = datetime.now(self.tz).strftime("%d.%m.%Y")
        yesterday = datetime.now(self.tz) - timedelta(days=1)
        yesterday = yesterday.strftime("%d.%m.%Y")
        date_trsp_start_input.send_keys(yesterday)
        date_trsp_end_input.send_keys(today)
        relatorio_button.click()

    def get_table_results(self):
        try:
            table = WebDriverWait(
                self.driver, config("timeout_loading_table_result")
            ).until(
                EC.presence_of_element_located(
                    (By.XPATH, config("portal_table_result_xpath").replace("||", "="))
                )
            )
        except:
            return pd.DataFrame()

        html_content = table.get_attribute("outerHTML")
        df = pd.read_html(StringIO(html_content))[0]
        df_filtered = df[df["Trsp."].notnull()]
        return df_filtered

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

    def process_ctes(self, ctes, df):
        for cte in ctes:
            dados = {
                "cte": cte.nconh,
                "doc_transp": cte.doctransp,
                "data_nf": cte.dtnotafisc,
                "valor_cte": cte.basecalc,
                "valor_usina": "",
                "diferenca_valor": "",
                "veiculo": cte.cdveiculo,
                "origem": cte.origem,
                "destino": cte.destino,
                "data": datetime.now(self.tz).strftime("%Y-%m-%d %H:%M:%S"),
                "msg": "",
                "alerta": False,
            }
            doc = str(cte.doctransp)
            doc = doc.replace(" ", "")
            line = df.loc[df["Trsp."] == doc]
            if line.empty:
                dados["msg"] = "CTE não encontrado no portal Vega"
                self.result_data.append(dados)
            else:
                usina_value = self.convert_str_to_float(
                    line["Valor Frete Líquido"].values[0]
                ) + self.convert_str_to_float(line["Impostos"].values[0])
                usina_value = round(usina_value, 2)
                diff = usina_value - cte.basecalc
                diff = round(diff, 2)
                if abs(diff) >= float(config("max_diff")):
                    msg = f"Diferença de valor encontrada"
                    dados["alerta"] = True
                else:
                    msg = f"OK"
                dados["valor_usina"] = usina_value
                dados["diferenca_valor"] = diff
                dados["msg"] = msg
                self.result_data.append(dados)

    def set_logs(self):
        for data in self.result_data:
            self.db_log.transaction(
                config("query_insert_log"),
                cte=data["cte"],
                doc_transp=data["doc_transp"],
                data_nf=data["data_nf"],
                valor_cte=data["valor_cte"],
                valor_usina=data["valor_usina"],
                diferenca_valor=data["diferenca_valor"],
                veiculo=data["veiculo"],
                origem=data["origem"],
                destino=data["destino"],
                data=data["data"],
                msg=data["msg"],
                alerta=data["alerta"],
            )

    def send_email(self, maestro, execution):
        for data in self.result_data:
            if data["alerta"]:
                val_usina = (
                    "R$ {:,.2f}".format(data["valor_usina"])
                    .replace(",", ";")
                    .replace(".", ",")
                    .replace(";", ".")
                )
                val_cte = (
                    "R$ {:,.2f}".format(data["valor_cte"])
                    .replace(",", ";")
                    .replace(".", ",")
                    .replace(";", ".")
                )
                diff = (
                    "R$ {:,.2f}".format(data["diferenca_valor"])
                    .replace(",", ";")
                    .replace(".", ",")
                    .replace(";", ".")
                )
                date_nf = datetime.strptime(data["data_nf"], "%Y-%m-%d").strftime(
                    "%d/%m/%Y"
                )
                message = f"N conhecimento: {data['cte']} - Placa: {data['veiculo']} - Data NFe: {date_nf} - Valor da Usina: {val_usina} - Valor do cte: {val_cte} - Valor divergente: {diff} - Origem: {data['origem']} - Destino: {data['destino']}"

                maestro.alert(
                    task_id=execution.task_id,
                    title="Frete com valores divergentes encontrado!",
                    message=message,
                    alert_type=AlertType.INFO,
                )

    def set_alert_table(self):
        alert_id = 16
        for data in self.result_data:
            if data["alerta"]:
                val_usina = (
                    "R$ {:,.2f}".format(data["valor_usina"])
                    .replace(",", ";")
                    .replace(".", ",")
                    .replace(";", ".")
                )
                val_cte = (
                    "R$ {:,.2f}".format(data["valor_cte"])
                    .replace(",", ";")
                    .replace(".", ",")
                    .replace(";", ".")
                )
                diff = (
                    "R$ {:,.2f}".format(data["diferenca_valor"])
                    .replace(",", ";")
                    .replace(".", ",")
                    .replace(";", ".")
                )
                date_nf = datetime.strptime(data["data_nf"], "%Y-%m-%d").strftime(
                    "%d/%m/%Y"
                )

                message = f"CTE EMITIDO COM VALOR DIVERGENTE. - conhecimento: {data['cte']} - Placa: {data['veiculo']} - Data NFe: {date_nf} - Valor da Usina: {val_usina} - Valor do cte: {val_cte} - Valor divergente: {diff} - Origem: {data['origem']} - Destino: {data['destino']}"

                self.db_sgt20.transaction(
                    config("query_insert_alert"), alert_id=alert_id, msg=message
                )


def main():
    try:
        maestro = BotMaestroSDK.from_sys_args()
        execution = maestro.get_execution()
        companys = {
            "vega": {"num": 1033163, "tags": ["%VE%"]},
            "vega_serra": {"num": 1082526, "tags": ["%XE%", "%X2%"]},
        }
        bot = PortalTransportador()
        bot.initialize_driver()
        bot.login()
        for company in companys:
            bot.navigate_to_portal()
            bot.select_company(companys[company]["num"])
            bot.navigate_to_custo_frete()
            bot.search_ctes()
            df = bot.get_table_results()
            if df.empty:
                continue
            dt_process = bot.get_data_processada()
            ctes = bot.get_data_ctes(
                tags=companys[company]["tags"], processados=dt_process
            )
            bot.process_ctes(ctes, df)
        bot.set_logs()
        bot.send_email(maestro, execution)
        bot.driver.quit()
        maestro.finish_task(
            task_id=execution.task_id,
            status=AutomationTaskFinishStatus.SUCCESS,
            message="Tarefa foi concluída com sucesso.",
        )
    except Exception as e:
        print(e)
        logger.error(e, exc_info=True)
        try:
            bot.driver.save_screenshot("erro.png")
            maestro.error(task_id=execution.task_id, exception=e, screenshot="erro.png")
        except:
            maestro.error(task_id=execution.task_id, exception=e)

        maestro.finish_task(
            task_id=execution.task_id,
            status=AutomationTaskFinishStatus.FAILED,
            message="Tarefa falhou.",
        )


if __name__ == "__main__":
    main()
