import discord

class menber:
    def __init__(self,text,num): # 初期化： インスタンス作成時に自動的に呼ばれる
        self.n = [text,num]
        self.name = []
        self.res = []
        self.resn =["(",0,")"]
        self.tmp = 0
    
    def add(self,name):
        if(self.n[1] > 0):
            self.n[1] -= 1
            self.name.append(name)
    
    def reserve(self,name):
        if len(self.res) == 0:
            self.tmp = 1
            self.res.append("仮" + name)
            for i in range(3):
                self.n.insert(2+i,self.resn[i])
            self.n[3] += 1
        else:
            self.res.append("仮" + name)
            self.n[3] += 1

    def sub(self,name):
        for i in range(len(self.name)):
            if self.name[i] == name:
                self.name.pop(i)
                self.n[1] += 1
                break

    def reservedel(self,name):
        for i in range(len(self.res)):
            if self.res[i] == "仮" + name:
                self.res.pop(i)
                self.n[3] -= 1
                break
        if len(self.res) == 0:
            self.tmp = 0
            for i in range(3):
                self.n.pop(2)

class guild:
    def __init__(self):
        self.mention = 0
        self.mentiondef = 0
        self.mentionnum = 3
        self.time = {}
        self.time_key = []
        self.msg = ""
    
    def set(self,time):
        send = time + "@"
        self.time[time] = menber(send,6)
        self.time_key = sorted(self.time.keys())

    def out(self,time):
        del self.time[time]
        self.time_key = sorted(self.time.keys())

    def clear(self,time):
        send = time + "@"
        self.time[time] = menber(send,6)
    

def nowhands(server):
    if len(server.time_key) == 0:
        embed=None
        m = "```\n" \
            + "交流戦の時間が登録されていません\n" \
            + "```"
        return m , embed
    else:
        if (server.mention == 1):
            mall = "@everyone\n"
            server.mention = 0
        else:
            mall = "\n"
        embed=discord.Embed(title="__***WAR LIST***__",color=0xee1111)
        #mwar = "**WAR LIST**\n"

        #mtmp = ""
        for i in server.time_key:
            if server.time[i].tmp == 1:
                mtmp = ">>> " + " , ".join(str(x) for x in server.time[i].name) + " " + " , ".join(str(x) for x in server.time[i].res)
                if mtmp == ">>> ":
                    mtmp = ">>> なし"
                embed.add_field(name="".join(str(x) for x in server.time[i].n), value=mtmp, inline=False)
            else:
                mtmp = ">>> " + " , ".join(str(x) for x in server.time[i].name)
                if mtmp == ">>> ":
                    mtmp = ">>> なし"
                embed.add_field(name="".join(str(x) for x in server.time[i].n), value=mtmp, inline=False)
        m = mall# + mwar + "```" + mtmp + "```"
    return m , embed

def help():
    embed=discord.Embed(title="__***Command List***__",color=0xee1111)
    embed.add_field(name="!set -> 交流戦時間の追加", value="例:!set 21 22 23 -> 21~23時の交流戦時間を追加する", inline=False)
    embed.add_field(name="!out -> 交流戦時間の削除", value="例:!out 21 22 23 -> 21~23時の交流戦時間を削除する", inline=False)
    embed.add_field(name="!c -> 挙手", value="!c 21      -> 21時に自分が追加される\n\t!c @non 21 -> 21時にnonが追加される", inline=False)
    embed.add_field(name="!rc -> 仮挙手", value="!rc 21      -> 21時に自分が仮で追加される\n\t!rc @non 21 -> 21時にnonが仮で追加される", inline=False)
    embed.add_field(name="!d -> 挙手取り下げ", value="!d 21      -> 21時の自分の挙手を取り下げる\n\t!d @non 21 -> 21時のnonの挙手を取り下げる", inline=False)
    embed.add_field(name="!rd -> 仮挙手取り下げ", value="!rd 21      -> 21時の自分の仮挙手を取り下げる\n\t!rd @non 21 -> 21時のnonの仮挙手を取り下げる", inline=False)
    embed.add_field(name="!now  -> 現在の挙手状況の確認", value="WAR LISTの表示", inline=False)
    embed.add_field(name="!mnow -> 現在の挙手状況の確認(everyoneメンション付)", value="WAR LISTの表示(everyoneメンション付)", inline=False)
    embed.add_field(name="!clear -> 挙手リセット", value="WAR LISTのリセット", inline=False)
    embed.add_field(name="!ch -> mention人数の設定", value="!ch 4   -> @4人になる時間に挙手したらメンションが付く\n※デフォルトは@3人", inline=False)
    return embed
