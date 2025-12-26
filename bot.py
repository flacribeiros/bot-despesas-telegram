from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from dateutil.relativedelta import relativedelta
import uuid

TOKEN = "8072970182:AAEF3RpodN7xPVK8fq1fpRjEoZO4YjT4NoA"
SPREADSHEET_NAME = "Despesas Telegram"

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name(
    "credenciais.json", scope
)
client = gspread.authorize(creds)
spreadsheet = client.open(SPREADSHEET_NAME)

# =========================
# UTILIDADES
# =========================
def get_month_sheet(date):
    title = date.strftime("%Y-%m")
    try:
        return spreadsheet.worksheet(title)
    except:
        ws = spreadsheet.add_worksheet(title=title, rows=1000, cols=10)
        ws.append_row(["ID", "Data", "Valor", "Categoria", "Descrição"])
        return ws

def total_mes(ws):
    valores = ws.col_values(3)[1:]
    return sum(float(v.replace(",", ".")) for v in valores)

def resumo_por_categoria(ws):
    dados = ws.get_all_values()[1:]
    resumo = {}

    for row in dados:
        categoria = row[3]
        valor = float(row[2].replace(",", "."))
        resumo[categoria] = resumo.get(categoria, 0) + valor

    texto = "📊 Resumo por categoria:\n"
    for cat, val in resumo.items():
        texto += f"• {cat}: R$ {val:.2f}\n"

    return texto

# =========================
# COMANDOS
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Olá! Eu sou seu bot de controle de despesas.\n\n"
        "Use os comandos:\n"
        "/gasto [valor] [categoria] [descrição] - Registrar um gasto\n"
        "/parcela [valor] [categoria] [descrição] [parcelas] - Registrar compra parcelada\n"
        "/apagar - Apagar o último registro"
    )

async def gasto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        valor = float(args[0].replace(",", "."))
        categoria = args[1]
        descricao = " ".join(args[2:])
        agora = datetime.now()

        ws = get_month_sheet(agora)
        ws.append_row([
            str(uuid.uuid4()),
            agora.strftime("%d/%m/%Y %H:%M"),
            f"{valor:.2f}",
            categoria,
            descricao
        ])

        total = total_mes(ws)
        resumo = resumo_por_categoria(ws)

        await update.message.reply_text(
            f"✅ Gasto registrado!\n"
            f"💰 Total do mês: R$ {total:.2f}\n\n"
            f"{resumo}"
        )
    except:
        await update.message.reply_text(
            "❌ Formato inválido.\nUse:\n/gasto 24,9 almoço mercado"
        )

async def parcela(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        total = float(args[0].replace(",", "."))
        categoria = args[1]
        parcelas = int(args[-1])
        descricao = " ".join(args[2:-1])

        valor_parcela = round(total / parcelas, 2)
        compra_id = str(uuid.uuid4())
        data = datetime.now()

        for i in range(parcelas):
            ws = get_month_sheet(data + relativedelta(months=i))
            ws.append_row([
                compra_id,
                (data + relativedelta(months=i)).strftime("%d/%m/%Y"),
                f"{valor_parcela:.2f}",
                categoria,
                f"{descricao} ({i+1}/{parcelas})"
            ])

        ws_atual = get_month_sheet(datetime.now())
        total_mes_atual = total_mes(ws_atual)
        resumo = resumo_por_categoria(ws_atual)

        await update.message.reply_text(
            f"✅ Compra parcelada registrada ({parcelas}x)\n"
            f"💰 Total do mês: R$ {total_mes_atual:.2f}\n\n"
            f"{resumo}"
        )
    except:
        await update.message.reply_text(
            "❌ Formato inválido.\nUse:\n/parcela 300 mercado cartão 3"
        )

async def apagar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ws = get_month_sheet(datetime.now())
    rows = ws.get_all_values()

    if len(rows) <= 1:
        await update.message.reply_text("❌ Nada para apagar.")
        return

    last_id = rows[-1][0]
    deleted = 0

    for worksheet in spreadsheet.worksheets():
        data = worksheet.get_all_values()
        for i in reversed(range(1, len(data))):
            if data[i][0] == last_id:
                worksheet.delete_rows(i + 1)
                deleted += 1

    await update.message.reply_text(
        f"🗑️ {deleted} registro(s) apagado(s) com sucesso."
    )

# =========================
# BOT
# =========================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))  # ✅ Adicionado
app.add_handler(CommandHandler(["gasto", "despesa"], gasto))
app.add_handler(CommandHandler("parcela", parcela))
app.add_handler(CommandHandler("apagar", apagar))

app.run_polling()
