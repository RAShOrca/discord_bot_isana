import discord
import os
import warnings  # FutureWarningを非表示にするため
from discord.ext import commands, tasks
from yahoo_fin import stock_info
from flask import Flask
from threading import Thread

# 🔧 FutureWarningを無視
warnings.filterwarnings("ignore", category=FutureWarning)

# 環境変数からトークンを取得
TOKEN = os.getenv('DISCORD_TOKEN')

# グローバル変数（ペアごとのアラート価格を辞書で管理）
pair_alerts = {}

# Yahoo Financeのティッカー変換表
TICKER_MAP = {
    'usdjpy': 'USDJPY=X',
    'nikkei': '^N225',
    'gold': 'GC=F'
}

# 補正値（MT5とYahoo Financeの差を考慮）
ADJUSTMENTS = {
    "nikkei": 116.1,
    "usdjpy": -1.225,
    "gold": -6.33
}

# インテント（ボットがメッセージの内容を取得するための権限）
intents = discord.Intents.default()
intents.message_content = True

# ボットのインスタンスを作成 (Application Commands用の設定に変更)
bot = commands.Bot(command_prefix="/", intents=intents, help_command=None)

# Flaskサーバーの設定
def create_app():
    app = Flask('')

    @app.route('/')
    def home():
        return "I'm alive!"

    return app

app = create_app()

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

@bot.event
async def on_ready():
    print(f'✨ I.S.A.N.A が起動しました！ ボット名: {bot.user}')
    price_watcher.start()  # 価格監視タスクを開始
    try:
        # スラッシュコマンドを再同期
        synced = await bot.tree.sync()
        print(f"🌐 スラッシュコマンドが {len(synced)} 個同期されました！")
    except Exception as e:
        print(f"⚠️ スラッシュコマンドの同期中にエラーが発生: {e}")

# /alert [ペア] [価格] コマンド
@bot.tree.command(name="alert", description="特定の通貨ペアにアラート価格を設定します")
async def alert(interaction: discord.Interaction, pair: str, price: float):
    if pair.lower() not in TICKER_MAP:
        await interaction.response.send_message(f"⚠️ 通貨ペア '{pair}' はサポートされていません。使用可能なペア: {', '.join(TICKER_MAP.keys())}")
        return

    if pair.lower() not in pair_alerts:
        pair_alerts[pair.lower()] = []

    pair_alerts[pair.lower()].append(price)
    await interaction.response.send_message(f"✅ 通貨ペア '{pair}' にアラート価格 {price} を追加しました！")

# /showlist コマンド
@bot.tree.command(name="showlist", description="現在のペアとアラート価格を表示します")
async def showList(interaction: discord.Interaction):
    if not pair_alerts:
        await interaction.response.send_message("現在、アクティブなアラートはありません。")
    else:
        msg = "📘 **現在のアクティブなアラート**\n"
        for pair, prices in pair_alerts.items():
            if prices:
                msg += f"🔹 **{pair.upper()}**: {', '.join(map(str, prices))}\n"
        await interaction.response.send_message(msg)

# /now [ペア] コマンド
@bot.tree.command(name="now", description="指定した通貨ペアの現在の価格を取得します")
async def now(interaction: discord.Interaction, pair: str):
    try:
        if pair.lower() in TICKER_MAP:
            ticker = TICKER_MAP[pair.lower()]
            adjustment = ADJUSTMENTS.get(pair.lower(), 0)  # 補正値を取得
        else:
            await interaction.response.send_message(f"⚠️ 通貨ペア '{pair}' はサポートされていません。使用可能なペア: {', '.join(TICKER_MAP.keys())}")
            return

        current_price = stock_info.get_live_price(ticker) + adjustment

        # 表示フォーマットを通貨ペアに応じて設定
        if pair.lower() == "usdjpy":
            current_price = f"{current_price:.3f}"  # 小数3桁
        elif pair.lower() == "gold":
            current_price = f"{current_price:.2f}"  # 小数2桁
        else:
            current_price = f"{current_price:.2f}"  # デフォルトは小数2桁

        await interaction.response.send_message(f"通貨ペア {pair.upper()} の現在の価格は **{current_price}** です！")
    except Exception as e:
        print(f"⚠️ 価格取得時のエラー: {e}")
        await interaction.response.send_message("⚠️ 価格を取得できませんでした。通貨ペアが正しいか確認してください。")

# /adjustprice [ペア] [補正値] コマンド
@bot.tree.command(name="adjustprice", description="通貨ペアの補正値を設定します")
async def adjustprice(interaction: discord.Interaction, pair: str, adjustment: float):
    if pair.lower() in ADJUSTMENTS:
        ADJUSTMENTS[pair.lower()] = adjustment
        await interaction.response.send_message(f"✅ 通貨ペア '{pair}' の補正値を {adjustment} に設定しました！")
    else:
        await interaction.response.send_message(f"⚠️ 通貨ペア '{pair}' はサポートされていません。使用可能なペア: {', '.join(ADJUSTMENTS.keys())}")

# /reset コマンド
@bot.tree.command(name="reset", description="すべての通貨ペアとアラート価格をリセットします")
async def reset(interaction: discord.Interaction):
    global pair_alerts
    pair_alerts.clear()
    await interaction.response.send_message("すべての通貨ペアとアラート価格がリセットされました！")

# /helpme コマンド
@bot.tree.command(name="helpme", description="利用可能なコマンドを一覧表示します")
async def help_command(interaction: discord.Interaction):
    help_text = (
        "📚 **I.S.A.N.A ボット コマンド一覧**\n"
        "/alert [ペア] [価格] - 特定の通貨ペアにアラート価格を設定します\n"
        "/showlist - 現在のアクティブなアラートを表示します\n"
        "/now [ペア] - 指定した通貨ペアの現在の価格を取得します\n"
        "/adjustprice [ペア] [補正値] - 通貨ペアの補正値を設定します\n"
        "/reset - すべての通貨ペアとアラート価格をリセットします\n"
    )
    await interaction.response.send_message(help_text)

# 価格監視タスク（10秒ごとに価格をチェック）
@tasks.loop(seconds=10)
async def price_watcher():
    for pair, alert_prices in list(pair_alerts.items()):
        if alert_prices:
            try:
                if pair.lower() in TICKER_MAP:
                    ticker = TICKER_MAP[pair.lower()]
                else:
                    continue

                current_price = stock_info.get_live_price(ticker)
                current_price = round(current_price + ADJUSTMENTS.get(pair.lower(), 0), 3 if pair.lower() == "usdjpy" else 2)

                for price in list(alert_prices):
                    if current_price >= price:
                        channel = discord.utils.get(bot.get_all_channels(), name="isana")
                        if channel:
                            await channel.send(f"🚨 **通貨ペア {pair.upper()} がアラート価格 {price} に到達しました！**\n**現在価格: {current_price}**")
                        pair_alerts[pair].remove(price)  # この価格だけを削除
            except Exception as e:
                print(f"⚠️ 価格取得時のエラー: {e}")

# サーバーを維持するためのkeep_alive関数を呼び出す
keep_alive()

# Discordボットを実行
bot.run(TOKEN)