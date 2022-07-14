import discord
from typing import Optional
from discord import AllowedMentions, app_commands
from discord.ext import commands,tasks
from discord.app_commands import AppCommandError
import boto3
import traceback
import json
from datetime import timedelta, timezone
import datetime
import os
import io
import re
import asyncio

TASK_LIST = []
tmp_task = {}

#discord情報欄
intents = discord.Intents.all()
token = os.environ['DISCORD_BOT_TOKEN']

#s3情報欄
accesckey = os.environ['KEY_ID']
secretkey = os.environ['SECRET_KEY_ID']
region = os.environ['REGION_NAME']
s3 = boto3.client('s3',aws_access_key_id=accesckey,aws_secret_access_key=secretkey,region_name=region)
bucket_name = "task-remind"

# ･ ～～  ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～
#s3からjsonファイルの取得
def get_s3file(bucket_name, key):
    s3 = boto3.resource('s3',aws_access_key_id=accesckey,aws_secret_access_key=secretkey,region_name=region)
    s3obj = s3.Object(bucket_name, key).get()
    return io.TextIOWrapper(io.BytesIO(s3obj['Body'].read()),encoding='utf-8')

#s3にjsonファイルのアップロード
def up_load():
    f_name = "./TASK_LIST.json"
    #with open("/tmp/"+str(id)+".json",'w', encoding='utf-8') as f:
    with open(f_name,'w', encoding='utf-8') as f:
        json.dump(TASK_LIST,f,ensure_ascii=False,indent=4)
    s3.upload_file(f_name,bucket_name,f_name[2:])

#未完了タスク計算
async def task_calc():
    count = 0
    for i in TASK_LIST:
        if i["status"] != "完了":
            count += 1
    await bot.change_presence(
        activity=discord.Activity(
            status=discord.Status.online,
            type=discord.ActivityType.watching,
            name=f'{count}個のタスク'
        )
    )

# ･ ～～  ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～
class detail_Modal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="詳細入力画面")
        self.timeout=None
    async def on_submit(self,interaction:discord.Interaction):
        await interaction.response.send_message("test")

# ･ ～～  ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～
#registコマンド用
class regist_OK(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.timeout=None
        self.add_item(Button_OK())
        self.add_item(Button_CANCEL())

class Button_OK(discord.ui.Button):
    def __init__(self):
        super().__init__(label='はい', style=discord.ButtonStyle.red)
    async def callback(self,interaction: discord.Interaction):
        TASK_LIST.append(tmp_task[str(interaction.user.id)])
        regist_num = tmp_task[str(interaction.user.id)]["no"]
        tmp_task.pop(str(interaction.user.id))
        await interaction.message.delete()
        await interaction.response.send_message(content=f'タスクの登録を完了しました\n登録管理番号は`{regist_num}`です\n管理番号は「`/task_list`」で確認できます')
        up_load()
        await task_calc()
        await asyncio.sleep(10)
        try:
            await interaction.delete_original_message()
        except:
            pass

class Button_CANCEL(discord.ui.Button):
    def __init__(self):
        super().__init__(label='キャンセル', style=discord.ButtonStyle.red)
    async def callback(self,interaction: discord.Interaction):
        tmp_task.pop(str(interaction.user.id))
        await interaction.message.delete()
        await interaction.response.send_message(content=f'タスクの登録をキャンセルしました')
        await asyncio.sleep(10)
        try:
            await interaction.delete_original_message()
        except:
            pass

# ･ ～～  ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～

class KyosyuBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!", 
            intents=intents,
            application_id = 694762011032158290
            )

    async def setup_hook(self):
        await self.add_cog(hundsup(bot))

class hundsup(commands.Cog):
    JST = timezone(timedelta(hours=9), 'JST')

    def __init__(self,bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.printer.start()

    #1時間毎にタスクアラーム検出処理
    @tasks.loop(minutes=1.0)
    async def printer(self):
        now = datetime.datetime.now(self.JST)
        print(now.strftime("%Y/%m/%d %H:%M"))
        #await channel.send(now)
        if now.strftime("%M") == '00':
            for i in TASK_LIST:
                if i["date"] != "未設定":
                    str_now = now.strftime("%Y/%m/%d %H:%M")
                    str_task = i["date"]
                    t_now = datetime.datetime.strptime(str_now,'%Y/%m/%d %H:%M')
                    t_task = datetime.datetime.strptime(str_task,'%Y/%m/%d %H:%M')
                    d_time = t_task - t_now
                    if (int(d_time.total_seconds()) == 86400) and (i["status"] != "完了"):
                        channel = bot.get_channel(i["channel"])
                        user = f'<@{i["user"]}>\n'
                        text = f'`{i["no"]}.`__**{i["title"]}**__ の期限24時間前です'
                        await channel.send(content=user+text)
                    if (int(d_time.total_seconds()) == 43200) and (i["status"] != "完了"):
                        channel = bot.get_channel(i["channel"])
                        user = f'<@{i["user"]}>\n'
                        text = f'`{i["no"]}.`__**{i["title"]}**__ の期限12時間前です'
                        await channel.send(content=user+text)
                    if (int(d_time.total_seconds()) == 3600) and (i["status"] != "完了"):
                        channel = bot.get_channel(i["channel"])
                        user = f'<@{i["user"]}>\n'
                        text = f'`{i["no"]}.`__**{i["title"]}**__ の期限1時間前です'
                        await channel.send(content=user+text)

    @app_commands.command(name = "show", description= 'タスクの詳細を表示する')
    async def show(
        self,
        interaction: discord.Interaction,
        number: int    #タスク管理番号
    ):
        #showコマンド用
        class edit_view(discord.ui.View):
            def __init__(self):
                super().__init__()
                self.timeout=None
                self.add_item(edit_Button(label='編集', style=discord.ButtonStyle.red))
                self.add_item(edit_status_Button(label='ステータス編集',style=discord.ButtonStyle.red))
                if TASK_LIST[number - 1]["task_conect"] != "child":
                    self.add_item(add_task(label='子タスク追加',style=discord.ButtonStyle.red))
                elif TASK_LIST[number - 1]["task_conect"] == "child":
                    self.add_item(delete_task(label='タスク連携解除',style=discord.ButtonStyle.blurple))

        class edit_Button(discord.ui.Button):
            async def callback(self, interaction: discord.Interaction):
                delete_msg = await interaction.channel.fetch_message(msg.id)
                await delete_msg.delete()
                modal = edit_modal(title='タスク編集',timeout=None)
                title = discord.ui.TextInput(label='タスク名', default=f'{TASK_LIST[number - 1]["title"]}',required=True)
                detail = discord.ui.TextInput(label='タスク詳細',style=discord.TextStyle.long, default=f'{TASK_LIST[number - 1]["detail"]}',required=False)
                date = discord.ui.TextInput(label='期限(yyyy/mm/dd hh:00形式)', default=f'{TASK_LIST[number - 1]["date"]}',required=False)
                comment = discord.ui.TextInput(label='タスク詳細',style=discord.TextStyle.long, placeholder=f'コメントを記入してください',required=False)
                modal.add_item(title)
                modal.add_item(detail)
                modal.add_item(date)
                modal.add_item(comment)
                async def e_on_submit(interaction: discord.Interaction):
                    ch_flag = False
                    ch_text = ""

                    if date.value != TASK_LIST[pos]["date"]:
                        if re.fullmatch(r'\d{4}/\d{1,2}/\d{1,2} \d{1,2}:00',str(date.value)) == None:
                            await interaction.response.send_message(content=f'期限の入力に誤りがあります')
                            await asyncio.sleep(10)
                            try:
                                await interaction.delete_original_message()
                            except:
                                pass
                            return
                        else:
                            ch_flag = True
                            ch_text += f'__**期限**__ : \n> {TASK_LIST[pos]["date"]} → {date}\n'
                            TASK_LIST[pos]["date"] = date.value if date.value != "" else "未設定"
                            pass
                    if title.value != TASK_LIST[pos]["title"]:
                        ch_flag = True
                        ch_text += f'__**タイトル**__ : \n> {TASK_LIST[pos]["title"]} → {title}\n'
                        TASK_LIST[pos]["title"] = title.value
                        pass
                    if detail.value != TASK_LIST[pos]["detail"]:
                        ch_flag = True
                        ch_text += f'__**詳細**__ : \n> {TASK_LIST[pos]["detail"]}\n> ↓\n> {detail.value if detail.value != "" else "未設定"}\n'
                        TASK_LIST[pos]["detail"] = detail.value if detail.value != "" else "未設定"
                        pass
                    if ch_flag:
                        JST = timezone(timedelta(hours=9), 'JST')
                        ch_text += f'に変更されました'
                        change_source = {
                            "変更内容" : ch_text,
                            "コメント" : comment.value if comment.value != "" else "",
                            "変更日時" : datetime.datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S"),
                            "編集者" : interaction.user.name
                        }
                        TASK_LIST[pos]["change"].append(change_source)
                        await interaction.response.send_message(content=ch_text)
                        up_load()
                        await asyncio.sleep(10)
                        try:
                            await interaction.delete_original_message()
                        except:
                            pass
                    else:
                        await interaction.response.send_message(content=f'変更内容がありませんでした')
                        await asyncio.sleep(10)
                        try:
                            await interaction.delete_original_message()
                        except:
                            pass
                modal.on_submit=e_on_submit
                await interaction.response.send_modal(modal)
                pass

        class edit_status_Button(discord.ui.Button):
            async def callback(self,interaction: discord.Interaction):
                await interaction.response.defer(thinking=True)
                view = discord.ui.View()
                select_menu = select_status()
                async def s_callback(interaction: discord.Interaction):
                    select_menu.disabled = False
                    if select_menu.values[0] == "完了":
                        flag = False
                        if TASK_LIST[pos]["task_conect"] == "parent":
                            for i in TASK_LIST[pos]["conect_no"]:
                                if TASK_LIST[i]["status"] != "完了":
                                    flag = True
                            if flag:
                                await interaction.response.send_message(content=f'子タスクが全て完了していないので、親タスクは完了に出来ません')
                                await asyncio.sleep(10)
                                try:
                                    await interaction.delete_original_message()
                                except:
                                    pass
                                return
                    TASK_LIST[pos]["status"] = select_menu.values[0]
                    delete_msg = await interaction.channel.fetch_message(tmp_msg.id)
                    await delete_msg.delete()
                    await interaction.response.send_message(f'タスクのステータスを **{select_menu.values[0]}** に変更しました')
                    up_load()
                    await task_calc()
                    await asyncio.sleep(10)
                    try:
                        await interaction.delete_original_message()
                    except:
                        pass
                select_menu.callback = s_callback
                view.add_item(select_menu)

                delete_msg = await interaction.channel.fetch_message(msg.id)
                await delete_msg.delete()
                tmp_msg = await interaction.followup.send(content=f'ステータスを選択してください',view=view)

        class select_status(discord.ui.Select):
            def __init__(self):
                option= [
                    "未着手",
                    "着手中",
                    "中断・保留",
                    "確認待ち",
                    "完了"
                    ]
                options = []
                for item in option:
                    options.append(discord.SelectOption(label=item, description=''))
            
                super().__init__(placeholder='', min_values=1, max_values=1, options=options)
                self.timeout=None

        class edit_modal(discord.ui.Modal):
            async def on_submit(self, interaction: discord.Interaction):
                await interaction.response.send_message(content=f'test')
                pass

        class add_task(discord.ui.Button):
            async def callback(self, interaction: discord.Interaction):
                count = 0
                for i in TASK_LIST:
                    if (i["task_conect"] == None) and (i["no"] != number):
                        count += 1
                if count == 0:
                    delete_msg = await interaction.channel.fetch_message(msg.id)
                    await delete_msg.delete()
                    await interaction.response.send_message(content=f'連携可能なタスクがありません')
                    await asyncio.sleep(10)
                    try:
                        await interaction.delete_original_message()
                    except:
                        pass
                    return
                await interaction.response.defer(thinking=True)
                view = discord.ui.View()
                select_menu = select_task()

                async def t_callback(interaction: discord.Interaction):
                    idx = select_menu.values[0].find(" : ")
                    t_pos = int(select_menu.values[0][:idx]) - 1
                    parent_task = TASK_LIST[number - 1]
                    parent_task["task_conect"] = "parent"
                    parent_task["conect_no"].append(t_pos)

                    child_task = TASK_LIST[t_pos]
                    child_task["task_conect"] = "child"
                    child_task["conect_no"].append(number - 1)

                    delete_msg = await interaction.channel.fetch_message(tmp_msg.id)
                    await delete_msg.delete()
                    await interaction.response.send_message(
                        f'親タスク : `{parent_task["no"]}.{parent_task["title"]}`\n'\
                        +f'子タスク : `{child_task["no"]}.{child_task["title"]}`\n'\
                        +f'で連携しました'
                        )
                    up_load()
                    await asyncio.sleep(10)
                    try:
                        await interaction.delete_original_message()
                    except:
                        pass
                    return
                
                select_menu.callback = t_callback
                view.add_item(select_menu)

                delete_msg = await interaction.channel.fetch_message(msg.id)
                await delete_msg.delete()
                tmp_msg = await interaction.followup.send(content=f'子に追加するタスクを選択してください',view=view)

        class select_task(discord.ui.Select):
            def __init__(self):
                option = []
                options = []
                for i in TASK_LIST:
                    if (i["task_conect"] == None) and (i["no"] != number):
                        option.append(f'{i["no"]} : {i["title"]}')
                for item in option:
                    options.append(discord.SelectOption(label=item, description=''))
            
                super().__init__(placeholder='', min_values=1, max_values=1, options=options)
                self.timeout=None

        class delete_task(discord.ui.Button):
            async def callback(self,interaction: discord.Interaction):
                await interaction.response.defer(thinking=True)
                
                p_pos = TASK_LIST[pos]["conect_no"][0]
                idx = TASK_LIST[p_pos]["conect_no"].index(pos)
                TASK_LIST[p_pos]["conect_no"].pop(idx)
                if len(TASK_LIST[p_pos]["conect_no"]) == 0:
                    TASK_LIST[p_pos]["task_conect"] = None
                TASK_LIST[pos]["task_conect"] = None
                TASK_LIST[pos]["conect_no"] = []

                delete_msg = await interaction.channel.fetch_message(msg.id)
                await delete_msg.delete()
                await interaction.followup.send(content=f'タスクの連携を解除しました')
                up_load()
                await asyncio.sleep(10)
                try:
                    await interaction.delete_original_message()
                except:
                    pass

        await interaction.response.defer(thinking=True)
        if number > len(TASK_LIST):
            await interaction.followup.send(content=f'そのタスク番号はありません')
            await asyncio.sleep(10)
            try:
                await interaction.delete_original_message()
            except:
                pass
            return
        pos = number - 1
        task = TASK_LIST[pos]
        embed = discord.Embed(title=f'__***タスク内容***__(No.{task["no"]})',color=0xee1111)
        embed.add_field(name="タスク名", value=task["title"], inline=True)
        embed.add_field(name="リマインド先",value=f'<#{task["channel"]}>', inline=True)
        embed.add_field(name="タスク詳細", value=task["detail"], inline=False)
        embed.add_field(name="期限", value=task["date"], inline=True)
        if task["user"] == "未設定":
            user = "未設定"
        else:
            tmp = await bot.fetch_user(task["user"])
            user = tmp.mention
        embed.add_field(name="担当者", value=user, inline=True)
        embed.add_field(name="ステータス", value=task["status"], inline=False)
        embed.set_footer(text=f'作成者 : {task["creater"]} , 作成日時 : {task["create_time"]}',icon_url=task["creater_icon"]) 
        if task["task_conect"] != None:
            if task["task_conect"] == "parent":
                child = ""
                for i in task["conect_no"]:
                    child += f'`{TASK_LIST[i]["no"]}.` {TASK_LIST[i]["title"]} ({TASK_LIST[i]["status"]})\n'
                embed.add_field(name="子タスク", value=child)
            if task["task_conect"] == "child":
                parent = f'`{TASK_LIST[task["conect_no"][0]]["no"]}.`{TASK_LIST[task["conect_no"][0]]["title"]}'
                embed.add_field(name="親タスク", value=parent)
        embed_list = [embed]
        if len(task["change"]) != 0:
            change_embed = discord.Embed(title=f'__***変更履歴***__',color=0x7f76f9)
            for i in task["change"]:
                change_date = i["変更日時"]
                change_text = f'__**編集者**__ : {i["編集者"]}\n'
                change_text += f'{i["変更内容"]}\n'
                if i["コメント"] != "":
                    change_text += f'__**コメント**__\n> {i["コメント"]}'
                change_embed.add_field(name=change_date,value=change_text,inline=False)
            embed_list.append(change_embed)
        
        view = edit_view()
        msg = await interaction.followup.send(content=f'',embeds=embed_list,view=view)
        await asyncio.sleep(20)
        try:
            await interaction.edit_original_message(view=None)
        except:
            pass
        return
    
    @app_commands.command(name = "regist", description= 'タスクの登録')
    async def regist(
        self,
        interaction: discord.Interaction,
        title: str,
        user: Optional[discord.User],
        date: str = None,
        hour: str = None,
        channel: Optional[discord.TextChannel] = None
    ):
        async def modal_on_submit(interaction: discord.Interaction):
            await interaction.response.defer(thinking=True)
            if (date != None) and (hour != None):
                input_date = f'{date} {hour}:00'
            elif (date != None) and (hour == None):
                input_date = f'{date} 00:00'
            elif (date == None):
                input_date = "未設定"
            embed = discord.Embed(title="__***タスク内容***__",color=0xee1111)
            embed.add_field(name="タスク名", value=title, inline=True)
            embed.add_field(name="リマインド先",value=f'<#{channel.id}>' if channel != None else f'<#{interaction.channel_id}>', inline=True)
            embed.add_field(name="タスク詳細", value=detail.value if detail.value != f'詳細を入力してください' else "未設定", inline=False)
            embed.add_field(name="期限", value=input_date, inline=True)
            embed.add_field(name="担当者", value=user.mention if user != None else "未設定", inline=True)
            embed.add_field(name="ステータス", value="未着手", inline=False)
            embed.set_footer(text=f'作成者 : {interaction.user.name} , 作成日時 : {datetime.datetime.now(self.JST).strftime("%Y-%m-%d %H:%M:%S")}',icon_url=interaction.user.avatar.url if interaction.user.avatar != None else None)
            
            #ﾀｽｸ内容ﾃﾞｰﾀ作成
            tmp_task[str(interaction.user.id)] = {
                "no" : len(TASK_LIST) + len(tmp_task) + 1,
                "title" : title,
                "detail" : detail.value if detail.value != f'詳細を入力してください' else "未設定",
                "date" : input_date,
                "user" : user.id if user != None else "未設定",
                "status" : "未着手",
                "creater" : interaction.user.name,
                "creater_icon" : interaction.user.avatar.url if interaction.user.avatar != None else None,
                "channel" : channel.id if channel != None else interaction.channel_id,
                "create_time" : str(datetime.datetime.now(self.JST).strftime("%Y-%m-%d %H:%M:%S")),
                "change" : [],
                "task_conect" : None,
                "conect_no" : []
            }

            await interaction.followup.send(content=f'こちらの内容でよろしいですか？',embed=embed,view=regist_OK())
            await asyncio.sleep(60)
            try:
                await interaction.delete_original_message()
                tmp_task.pop(str(interaction.user.id))
                await interaction.followup.send(content=f'タスクの登録をキャンセルしました')
            except:
                pass
            return

        if ((date != None)  and (re.fullmatch(r'\d{4}/\d{1,2}/\d{1,2}',str(date)) == None)) or ((hour != None) and (re.fullmatch(r'\d{1,2}',str(hour)) == None)):
            await interaction.response.send_message(content=f'日付または時間の入力にエラーがあります')
            return
        
        if (date == None) and (hour != None):
            await interaction.response.send_message(content=f'時間のみの指定はできません')
            return

        modal = detail_Modal()
        detail = discord.ui.TextInput(label=f'詳細',style=discord.TextStyle.long,default=f'詳細を入力してください',required=False)
        modal.add_item(detail)
        modal.on_submit = modal_on_submit
        await interaction.response.send_modal(modal)

    @app_commands.command(name = "task_list",description= 'タスク一覧を表示する')
    async def task_list(
        self,
        interaction: discord.Interaction,
    ):
        await interaction.response.defer(thinking=True)
        task_title = ""
        cmp_title = ""
        count = 0
        embed = discord.Embed(color=0xee1111)
        cmp_embed = discord.Embed(color=0xee1111)
        if len(TASK_LIST) == 0:
            task_title = "まだタスクが登録されていません"
        else:
            tmp_task_list = sorted(TASK_LIST, key=lambda x: x['date'])
            for i in tmp_task_list:
                count += 1
                if i["status"] == "完了":
                    if i["task_conect"] != "child":
                        cmp_title = f'`{i["no"]}.` **{str(i["title"])}** (`期限 :` {i["date"]}) `担当者 :` <@{i["user"]}>\n'
                        if i["task_conect"] == "parent":
                            cmp_title += "> |- 子タスク有り\n"
                elif i["task_conect"] != "child":
                    task_title += f'`{i["no"]}.` **{str(i["title"])}** (`期限 :` {i["date"]}) `担当者 :` <@{i["user"]}>\n'
                    if i["task_conect"] == "parent":
                        task_title += "> |- 子タスク有り\n"
        embed.add_field(name="__***タスク一覧***__",value=task_title)
        cmp_embed.add_field(name="__***完了タスク一覧***__",value=cmp_title)
        embed_list = []
        if task_title != "":
            embed_list.append(embed)
        if cmp_title != "":
            embed_list.append(cmp_embed)
        await interaction.followup.send(embeds=embed_list)

    @app_commands.command(name = "edit",description= 'タスクの編集(担当者、通知先)')
    async def edit(
        self,
        interaction: discord.Interaction,
        number: int,
        user: Optional[discord.User] = None,
        channel: Optional[discord.TextChannel] = None
    ):
        if (user == None) and (channel == None):
            await interaction.response.send_message(content=f'編集内容がありません')
            await asyncio.sleep(10)
            try:
                await interaction.delete_original_message()
            except:
                pass
            return
        pos = number - 1
        ch_flag = False
        ch_text = ""
        await interaction.response.defer(thinking=True)
        if user != None:
            if (user.id != TASK_LIST[pos]["user"]):
                ch_flag = True
                ch_text += f'__**担当者**__ : \n> <@{TASK_LIST[pos]["user"]}> → <@{user.id}>\n'
                TASK_LIST[pos]["user"] = user.id
        if channel != None:
            if (channel.id != TASK_LIST[pos]["channel"]):
                ch_flag = True
                ch_text += f'__**リマインド先**__ : \n> <#{TASK_LIST[pos]["channel"]}> → <#{channel.id}>\n'
                TASK_LIST[pos]["channel"] = channel.id
        if ch_flag:
            JST = timezone(timedelta(hours=9), 'JST')
            ch_text += f'に変更されました'
            change_source = {
                "変更内容" : ch_text,
                "コメント" : "",
                "変更日時" : datetime.datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S"),
                "編集者" : interaction.user.name
            }
            TASK_LIST[pos]["change"].append(change_source)
            await interaction.followup.send(content=ch_text)
            up_load()
            await asyncio.sleep(10)
            try:
                await interaction.delete_original_message()
            except:
                pass
        else:
            await interaction.followup.send(content=f'変更内容がありませんでした')
            await asyncio.sleep(10)
            try:
                await interaction.delete_original_message()
            except:
                pass

    @app_commands.command(name = "delete",description= 'タスクの削除')
    async def delete(
        self,
        interaction: discord.Interaction,
        number: int
    ):
        class delete_view(discord.ui.View):
            def __init__(self):
                super().__init__()
                self.timeout=None
                self.add_item(delete_OK())
                self.add_item(delete_CANCEL())
        
        class delete_OK(discord.ui.Button):
            def __init__(self):
                super().__init__(label='はい', style=discord.ButtonStyle.red)
            async def callback(self, interaction: discord.Interaction):
                delete_msg = await interaction.channel.fetch_message(msg.id)
                await delete_msg.delete()
                await interaction.response.defer(thinking=True)

                if TASK_LIST[pos]["task_conect"] == None:
                    TASK_LIST.pop(pos)
                elif TASK_LIST[pos]["task_conect"] == "child":
                    parent_task_pos = TASK_LIST[pos]["conect_no"][0]
                    idx = TASK_LIST[parent_task_pos]["conect_no"].index(pos)
                    TASK_LIST[parent_task_pos]["conect_no"].pop(idx)
                    if len(TASK_LIST[parent_task_pos]["conect_no"]) == 0:
                        TASK_LIST[parent_task_pos]["task_conect"] = None
                    TASK_LIST.pop(pos)
                elif TASK_LIST[pos]["task_conect"] == "parent":
                    for i in TASK_LIST[pos]["conect_no"]:
                        TASK_LIST[i]["task_conect"] = None
                        TASK_LIST[i]["conect_no"] = []
                    TASK_LIST.pop(pos)
                
                #タスク管理番号の繰り上げ
                if len(TASK_LIST) != 0:
                    for i in range(pos,len(TASK_LIST)):
                        TASK_LIST[i]["no"] -= 1
                
                await interaction.followup.send(content=f'タスクを削除しました')
                up_load()
                await task_calc()
                await asyncio.sleep(60)
                try:
                    await interaction.delete_original_message()
                except:
                    pass
        
        class delete_CANCEL(discord.ui.Button):
            def __init__(self):
                super().__init__(label='キャンセル', style=discord.ButtonStyle.red)
            async def callback(self, interaction: discord.Interaction):
                delete_msg = await interaction.channel.fetch_message(msg.id)
                await delete_msg.delete()
                await interaction.response.send_message(content=f'タスクの削除をキャンセルしました')
                await asyncio.sleep(10)
                try:
                    await interaction.delete_original_message()
                except:
                    pass
                
        await interaction.response.defer(thinking=True)
        if number > len(TASK_LIST):
            await interaction.followup.send(content=f'そのタスク番号はありません')
            await asyncio.sleep(10)
            try:
                await interaction.delete_original_message()
            except:
                pass
            return
        pos = number - 1
        task = TASK_LIST[pos]
        embed = discord.Embed(title=f'__***タスク内容***__(No.{task["no"]})',color=0xee1111)
        embed.add_field(name="タスク名", value=task["title"], inline=True)
        embed.add_field(name="リマインド先",value=f'<#{task["channel"]}>', inline=True)
        embed.add_field(name="タスク詳細", value=task["detail"], inline=False)
        embed.add_field(name="期限", value=task["date"], inline=True)
        if task["user"] == "未設定":
            user = "未設定"
        else:
            tmp = await bot.fetch_user(task["user"])
            user = tmp.mention
        embed.add_field(name="担当者", value=user, inline=True)
        embed.add_field(name="ステータス", value=task["status"], inline=False)
        embed.set_footer(text=f'作成者 : {task["creater"]} , 作成日時 : {task["create_time"]}',icon_url=task["creater_icon"]) 
        if task["task_conect"] != None:
            if task["task_conect"] == "parent":
                child = ""
                for i in task["conect_no"]:
                    child += f'`{TASK_LIST[i]["no"]}.` {TASK_LIST[i]["title"]}\n'
                embed.add_field(name="子タスク", value=child)
            if task["task_conect"] == "child":
                parent = f'`{TASK_LIST[task["conect_no"][0]]["no"]}.`{TASK_LIST[task["conect_no"][0]]["title"]}'
                embed.add_field(name="親タスク", value=parent)
        if len(task["change"]) != 0:
            for i in task["change"]:
                change_date = i["変更日時"]
                change_text = f'__**編集者**__ : {i["編集者"]}\n'
                change_text += f'{i["変更内容"]}\n'
                if i["コメント"] != "":
                    change_text += f'__**コメント**__\n> {i["コメント"]}'
                embed.add_field(name=change_date,value=change_text,inline=False)
        
        view = delete_view()
        msg = await interaction.followup.send(content=f'こちらのタスクを削除しますか？',embed=embed,view=view)
        

# ･ ～～  ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～
# ･ ～～  ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～ ･ ～～

bot = KyosyuBot()
tree = bot.tree

@bot.event
async def on_ready():
    global TASK_LIST
    TASK_LIST = json.load(get_s3file(bucket_name, "TASK_LIST.json"))
    await task_calc()

@tree.error
async def on_app_command_error(interaction: discord.Interaction, error: AppCommandError) -> None:
    t = list(traceback.TracebackException.from_exception(error).format())
    mes = t[2] + t[-1]#"".join(t)
    ch = 990794002649452565
    embed = discord.Embed(title="エラー情報", description="", color=0xf00)
    embed.add_field(name="エラー発生サーバー名", value=interaction.guild.name, inline=False)
    embed.add_field(name="エラー発生サーバーID", value=interaction.guild.id, inline=False)
    embed.add_field(name="エラー発生チャンネルID", value=interaction.channel_id, inline=False)
    embed.add_field(name="エラー発生ユーザー名", value=interaction.user.name, inline=False)
    embed.add_field(name="エラー発生ユーザーID", value=interaction.user.id, inline=False)
    #embed.add_field(name="エラー発生コマンド", value=interaction.data, inline=False)
    embed.add_field(name="発生エラー", value=mes, inline=False)
    m = await bot.get_channel(ch).send(embed=embed)
    message = \
        "何らかのエラーが発生しました。ごめんなさい。\n"\
        +f"このエラーについて問い合わせるときはこのコードも一緒にお知らせください：{id}"
    embed=discord.Embed(title="__***連絡先***__",color=0xffffff)
    embed.add_field(name="twitter", value="[@enoooooooon](https://twitter.com/enoooooooon)", inline=True)
    embed.add_field(name="discord", value="non#0831", inline=True)
    await interaction.followup.send(content=message,embed=embed)

bot.run(token)
