from botcity.maestro import *
from main import PortalTransportador
from datetime import datetime, timedelta
from db import db_logs

BotMaestroSDK.RAISE_NOT_CONNECTED = False


def main():
    maestro = BotMaestroSDK.from_sys_args()
    execution = maestro.get_execution()
    portal_password = maestro.get_credential(
        label="consulta_PortalTransportador", key="PORTAL_PASSWORD"
    )
    db_password = maestro.get_credential(
        label="consulta_PortalTransportador", key="DB_PASSWORD"
    )
    user_db = maestro.get_credential(label="db_log", key="user")
    password_db = maestro.get_credential(label="db_log", key="password")
    try:
        bot = PortalTransportador(execution.parameters, portal_password, db_password)
        bot.connect_to_postgres()
        bot.get_cte_tg99()
        db = db_logs(user_db, password_db)
        data = db.get_alerts()
        filter_data = []
        for cte_num in bot.cte_nums:
            skip = False
            for item in data:
                if item[0] == cte_num[0] and item[1] != "Não encontrado na base Vega":
                    skip = True
                    break
            if not skip:
                filter_data.append(cte_num)
        bot.cte_nums = filter_data
        print(bot.cte_nums)

        if len(bot.cte_nums) > 0:
            bot.initialize_driver()
            bot.login()
            bot.navigate_to_portal()
            bot.select_company()
            bot.navigate_to_custo_frete()
            bot.search_ctes()
            bot.get_table_result()
            bot.format_data_table()
            bot.verify_value_ctes()

            for data in bot.data:
                alerta = "Não"
                if data[5] == "Diferença de valor encontrada":
                    bot.navigate_to_menu()
                    bot.navigate_to_ordens_page()
                    is_high_weight = bot.verify_weight_coil(data[9])
                    val_usina = (
                        "R$ {:,.2f}".format(data[6])
                        .replace(",", ";")
                        .replace(".", ",")
                        .replace(";", ".")
                    )
                    val_cte = (
                        "R$ {:,.2f}".format(data[7])
                        .replace(",", ";")
                        .replace(".", ",")
                        .replace(";", ".")
                    )
                    diff = (
                        "R$ {:,.2f}".format(data[8])
                        .replace(",", ";")
                        .replace(".", ",")
                        .replace(";", ".")
                    )
                    date_nf = datetime.strptime(data[4], "%Y-%m-%d").strftime(
                        "%d/%m/%Y"
                    )

                    if is_high_weight:
                        message = f"* Existe uma bobina com 20T ou mais nesse transporte * \n N conhecimento: {data[1]} - Placa: {data[2]} - Data NFe: {date_nf} - Valor da Usina: {val_usina} - Valor do cte: {val_cte} - Valor divergente: {diff}"
                    else:
                        message = (
                            f"N conhecimento: {data[1]} - Placa: {data[2]} - Data NFe: {date_nf} - Valor da Usina: {val_usina} - Valor do cte: {val_cte} - Valor divergente: {diff}",
                        )

                    maestro.alert(
                        task_id=execution.task_id,
                        title="Frete com valores divergentes encontrado!",
                        message=message,
                        alert_type=AlertType.INFO,
                    )
                    alerta = "Sim"
                db.insert_logs(data[1], data[5])

                maestro.new_log_entry(
                    activity_label="consulta_PortalTransportador",
                    values={
                        "nconh": data[1],
                        "placa": data[2],
                        "motorista": data[3],
                        "dtnotafisc": data[4],
                        "msg": data[5],
                        "usina_value": data[6],
                        "cte_value": data[7],
                        "diff": data[8],
                        "alerta": alerta,
                    },
                )

        maestro.finish_task(
            task_id=execution.task_id,
            status=AutomationTaskFinishStatus.SUCCESS,
            message="Tarefa foi concluída com sucesso.",
        )

    except Exception as erro:
        print(f"Erro inesperado: {erro}")
        try:
            bot.driver.save_screenshot("erro.png")
            maestro.error(
                task_id=execution.task_id, exception=erro, screenshot="erro.png"
            )
        except:
            maestro.error(task_id=execution.task_id, exception=erro)

        maestro.finish_task(
            task_id=execution.task_id,
            status=AutomationTaskFinishStatus.FAILED,
            message="Tarefa falhou.",
        )

    finally:
        bot.close_driver()


if __name__ == "__main__":
    main()
