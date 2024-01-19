from botcity.maestro import *
from main import PortalTransportador
from datetime import datetime, timedelta

BotMaestroSDK.RAISE_NOT_CONNECTED = False



def main():
    maestro = BotMaestroSDK.from_sys_args()
    execution = maestro.get_execution()
    portal_password = maestro.get_credential(label="consulta_PortalTransportador", key="PORTAL_PASSWORD")
    db_password = maestro.get_credential(label="consulta_PortalTransportador", key="DB_PASSWORD")
    
    try:
        bot = PortalTransportador(execution.parameters, portal_password, db_password)
        bot.connect_to_postgres()
        bot.get_cte_tg99()
        date = (datetime.now() - timedelta(days=3))
        date = date.strftime("%d/%m/%Y")
        data = maestro.get_log(activity_label="consulta_PortalTransportador", date=date)
        
        for cte_num in bot.cte_nums:
            for item in data:
                if item['nconh'] == cte_num[0] and item['msg'] != "Não encontrado na base Vega" and item['alerta'] == "Sim":
                    bot.cte_nums.remove(cte_num)
                    break  
        
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
                alerta = 'Não'
                if data[5] == "Diferença de valor encontrada":
                    val_usina = "R$ {:,.2f}".format(val_usina).replace(",", ";").replace(".", ",").replace(";", ".")
                    val_cte = "R$ {:,.2f}".format(val_cte).replace(",", ";").replace(".", ",").replace(";", ".")
                    diff = "R$ {:,.2f}".format(diff).replace(",", ";").replace(".", ",").replace(";", ".")
                    date_nf = datetime.strptime(data[4], "%Y-%m-%d").strftime("%d/%m/%Y")
                    maestro.alert(
                        task_id=execution.task_id,
                        title="Frete com valores divergentes encontrado!",
                        message= f"N conhecimento: {data[1]} - Placa: {data[2]} - Data NFe: {date_nf} - Valor da Usina: {val_usina} - Valor do cte: {val_cte} - Valor divergente: {diff}",
                        alert_type=AlertType.INFO
                    )
                    alerta = 'Sim'
                    
                maestro.new_log_entry(
                    activity_label="consulta_PortalTransportador",
                    values = {
                        "nconh": data[1],
                        "placa": data[2],
                        "motorista": data[3],
                        "dtnotafisc": data[4],
                        "msg": data[5],
                        "usina_value": data[6],
                        "cte_value": data[7],
                        "diff": data[8],
                        "alerta": alerta
                    }
                )
                
        maestro.finish_task(
            task_id=execution.task_id,
            status=AutomationTaskFinishStatus.SUCCESS,
            message="Tarefa foi concluída com sucesso."
        ) 
        
    except Exception as erro:
        print(f"Erro inesperado: {erro}")
        try:
            bot.driver.save_screenshot('erro.png')
            maestro.error(
                task_id=execution.task_id,
                exception=erro,
                screenshot='erro.png'
            )
        except:
            maestro.error(
                task_id=execution.task_id,
                exception=erro
            )
            
        maestro.finish_task(
            task_id=execution.task_id,
            status=AutomationTaskFinishStatus.FAILED,
            message="Tarefa falhou."
        )
        
    finally:
        bot.close_driver()


if __name__ == '__main__':
    main()
