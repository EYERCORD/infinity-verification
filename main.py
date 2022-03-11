#тут очень много говно кода (переписывать времени не было, поэтому перепишу позже)



from flask import Flask, abort, request, redirect, render_template, session, send_file, url_for
from oauth import Oauth
import random
import pymongo
from pymongo import MongoClient
from captcha.image import ImageCaptcha
import time, random, string
import os
import requests


ok = [200, 201, 204]
generator = ImageCaptcha()

for x in os.listdir('tmp/'):
    if x.endswith('.png'): os.remove(f'tmp/{x}')
      
from requests_oauthlib import OAuth2Session

OAUTH2_CLIENT_ID = '' #ид бота
OAUTH2_CLIENT_SECRET = '' #client_secret приложения
OAUTH2_REDIRECT_URI = 'https://infinity-verification.ml/session' # редирект ссылка (нужно поменять лишь первую часть https://infinity-verification.ml на свою) + на странице разработчиков в вашем приложении тоже нужно добавить эту ссылку

API_BASE_URL = os.environ.get('API_BASE_URL', 'https://discordapp.com/api')
AUTHORIZATION_BASE_URL = API_BASE_URL + '/oauth2/authorize'
TOKEN_URL = API_BASE_URL + '/oauth2/token'
# os.system('clear')

token = '' #токен бота


def ban(id, gid):
    r = requests.put(f'https://discord.com/api/guilds/{gid}/bans/{id}', headers={'Authorization': f'Bot {token}'})
    return r.status_code


def add_role(mid, rid, gid):
    r = requests.put(f'https://discord.com/api/guilds/{gid}/members/{mid}/roles/{rid}',
                     headers={'Authorization': f'Bot {token}'})
    return r.status_code





cluster = MongoClient(
    '') #база данных для хранения настроек серверов
db = cluster.verify
configs = db.configs


app = Flask(__name__)
app.config['SECRET_KEY'] = 'very_very_secret_key'

if 'https://' in OAUTH2_REDIRECT_URI: #если у вас в юрл http, ставите http
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = 'true'

def make_session(token=None, state=None, scope=None):
    return OAuth2Session(
        client_id=OAUTH2_CLIENT_ID,
        token=token,
        state=state,
        scope=scope,
        redirect_uri=OAUTH2_REDIRECT_URI,
        auto_refresh_kwargs={
            'client_id': OAUTH2_CLIENT_ID,
            'client_secret': OAUTH2_CLIENT_SECRET,
        },
        auto_refresh_url=TOKEN_URL,
        token_updater=token_updater)

def token_updater(token):
    session['oauth2_token'] = token





def imgurl(t, uid, id, size):
    gif = f"https://cdn.discordapp.com/{t}s/{uid}/{id}.gif?size={size}"
    gif_small = f"https://cdn.discordapp.com/{t}s/{uid}/{id}.gif?size=16"
    png = f"https://cdn.discordapp.com/{t}s/{uid}/{id}.png?size={size}"
    print('===')
    print(gif)
    print(png)
    print('===')
    return gif if requests.get(gif_small).status_code == 200 else png


captcha_images = {}
'''
    Используется для сохранения кода юзера, решение капчи и время создания
    Капча должна быть удалена если она создана минуту назад или юзер ввёл ответ, неважно правильный или нет
'''
@app.route('/exit')
def exit_():
  session['oauth2_token'] = None
  return redirect('https://infinity-verification.ml')
  
  
@app.route('/captcha/<id>.png')
def captcha_make(id):
    global captcha_images

    if id in captcha_images:
        if os.path.isfile(f'tmp/{id}.png'):
            return send_file(f'tmp/{id}.png')
        else:
            del captcha_images[id]
    txt = ''
    todel = []
    for x in captcha_images:
        if captcha_images[x]['time'] + 60 >= time.time():
            if os.path.exists(f'tmp/{id}.png'): os.remove(f'tmp/{id}.png')
            todel.append(x)

    for x in todel:
        del captcha_images[x]

    for x in range(3):
        txt += random.choice(string.ascii_lowercase)
    generator.write(txt, f'tmp/{id}.png')
    captcha_images[id] = {
        'solve': txt,
        'time': time.time()
    }
    return send_file(f'tmp/{id}.png')







@app.route('/session')
def callback():
    if request.values.get('error'):
        return request.values['error']
    discord = make_session(state=session.get('oauth2_state'))
    token = discord.fetch_token(
        TOKEN_URL,
        client_secret=OAUTH2_CLIENT_SECRET,
        authorization_response=request.url)
    session['oauth2_token'] = token
    return redirect(url_for('.login'))


@app.route('/login', methods=['get'])
def get_guild():
    ggg = False
    code = session.get('oauth2_state')
    guild = session.get('guild_id')
    if guild is None:
      return redirect('ссылка на главную страницу')
    try: 
      discord = make_session(token=session.get('oauth2_token'))
      user = discord.get(API_BASE_URL + '/users/@me').json()
      usr_tag = user['discriminator']
      usr_name = user['username']
      usr = f'Вход выполнен как: {usr_name}#{usr_tag}'
    except:
      return redirect(url_for('.verification_'))
      user = 'Вы не авторизованы!'
    return render_template('server.html', code=code, guild_id = guild, login = {'user': usr, 'server': configs.find_one({'_id': int(guild)})['guild_name']})


def send_logs(title, user_id, user, avatar, banner):
    j = {
        'embeds': [{
            'color': 0,
            'title': title,
            'fields': [{
                'name': 'ID:',
                'value': user_id,
                'inline': False
            }, {
                'name': 'Никнейм',
                'value': f'{user}',
                'inline': False
            }],
            "image": {
                "url": imgurl('banner', user_id, banner, 1024),
                # f"https://cdn.discordapp.com/banners/{user_json['id']}/{user_json['banner']}.png?size=1024"
            },
            "thumbnail": {
                "url": imgurl('avatar', user_id, avatar, 1024)
                # f"https://cdn.discordapp.com/avatars/{user_json['id']}/{user_json['avatar']}.webp?size=1024"
            },
        }],
        'username': f"{user}",
        'avatar_url': imgurl('avatar', user_id, avatar, 1024)
        # f"https://cdn.discordapp.com/avatars/{user_json['id']}/{user_json['avatar']}.webp?size=128"
    }
    return j

@app.before_request
def make_session_permanent():
    session.permanent = True

@app.route("/", methods=["get"])
def index():
    #configs.update_one({"_id": 877156048979501067}, {'$set': {'guild_name': 'Infinity Shield', 'guild_avatar': 'https://cdn.discordapp.com/avatars/878689287284092958/86d3524555df764823b8d0f72b1d123e.webp?size=256', 'guild_owner': 'ProBAN#1559', 'guild_owner_avatar': 'https://cdn.discordapp.com/avatars/658947623364984834/ccabf51696ed8f200adff4be51c43a65.webp?size=1024', 'guild_members': 206, 'support': 'https://discord.gg/'}})
    #print('g')
    return render_template('general.html')

@app.route('/servers/<server_id>')
def servers_(server_id: int):
  server_id = int(server_id)
  try: configs.find_one({"_id": server_id})['guild_name']
  except: return redirect('https://infinity-verification.ml')
  try: int(server_id)
  except: return redirect('https://infinity-verification.ml')
  session['guild_id'] = int(server_id)
  try: 
      discord = make_session(token=session.get('oauth2_token'))
      user = discord.get(API_BASE_URL + '/users/@me').json()
      usr_tag = user['discriminator']
      usr_name = user['username']
      usr = f'{usr_name}#{usr_tag}'
      session['guild_id'] = int(server_id)
  except:
      usr = 'Гость'
  server1 = {'guild_name': configs.find_one({"_id": server_id})['guild_name'], 'guild_owner': configs.find_one({"_id": server_id})['guild_owner'], 'guild_owner_avatar': configs.find_one({"_id": server_id})['guild_owner_avatar'], 'guild_members': configs.find_one({"_id": server_id})['guild_members'], 'guild_avatar': configs.find_one({"_id": server_id})['guild_avatar']}
  return render_template('servers.html', server=server1, usr=usr)
  #return redirect(url_me('.verification'))
  
@app.route('/verification')
def verification_():
    scope = request.args.get(
        'scope',
        'identify guilds')
    discord = make_session(scope=scope.split(' '))
    authorization_url, state = discord.authorization_url(AUTHORIZATION_BASE_URL)
    session['oauth2_state'] = state
    return redirect(authorization_url)

@app.route("/login", methods=["POST"])
def login():
    try: 
      discord = make_session(token=session.get('oauth2_token'))
      user = discord.get(API_BASE_URL + '/users/@me').json()
      usr_tag = user['discriminator']
      usr_name = user['username']
      usr = f'{usr_name}#{usr_tag}'
    except:
      usr = 'Гость'
      return redirect(url_for('.verification'))
    code = "ban"
    
    # return 'Тех. работы'
    guild = session.get('guild_id')
    text = guild
    
    try: text = int(guild)
    except: return render_template('error.html', code=request.args.get('code'), error = 'Ошибка! Неверный сервер', login = {'user': usr, 'server': 'undefined'})
    dt = {'user': usr, 'server': configs.find_one({"_id": int(guild)})['guild_name']}
    try:
        bl = configs.find_one({"_id": int(text)})['bl_servers']
    except:
      return render_template('error.html', code=request.args.get('code'), error = 'Ошибка! Неверный сервер', login = dt)
    md = configs.find_one({"_id": int(guild)})['mode']
    if md is None:
      md = False
    if md:
      return render_template('error.html', code=request.args.get('code'), error = 'Ошибка! Данный сервер закрыт', login = dt)
    role_id = configs.find_one({"_id": int(text)})['role']
    web_url = configs.find_one({"_id": int(text)})['webhook']
    premium = configs.find_one({"_id": int(text)})['premium']
    if web_url is None:
        return render_template('error.html', code=request.args.get('code'), error = 'Ошибка! В конфигах этого сервера не обнаружено вебхука', login = dt)
    if role_id is None:
        return render_template('error.html', code=request.args.get('code'), error = 'Ошибка! В конфигах этого сервера не обнаружено роли', login = dt)
    ban_user = False
    try: 
      discord = make_session(token=session.get('oauth2_token'))
      user = discord.get(API_BASE_URL + '/users/@me').json()
      guilds = discord.get(API_BASE_URL + '/users/@me/guilds').json()
    #code = request.args.get("code")
    except:
        return render_template('error.html', code=request.args.get('code'), error = "Ошибка! Вы не авторизованы", login = dt)

    username, usertag = user.get("username"), user.get("discriminator")
    user_json = user
    # email = user_json.get('email')
    usr = f"{username}#{usertag}"
    n = '\n'
    o = []
    for k in user:
        o.append(f'{k}: {user_json[k]}')
    try:avatar = imgurl('avatar', user_json['id'], user_json['avatar'], 1024)
    except: return redirect('https://infinity-verification.ml/verification')
    banner = imgurl('banner', user_json['id'], user_json['banner'], 1024)
    j2 = {
        'embeds': [{
            'color': user_json['accent_color'] or 0,
            'title': 'Пользователь не прошел верификацию',
            'fields': [{
                'name': 'ID:',
                'value': user_json['id'],
                'inline': False
            }, {
                'name': 'Имя и тег:',
                'value': f'{username}#{usertag}',
                'inline': False
            }],
            "image": {
                "url": banner,
                # f"https://cdn.discordapp.com/banners/{user_json['id']}/{user_json['banner']}.png?size=1024"
            },
            "thumbnail": {
                "url": avatar
                # f"https://cdn.discordapp.com/avatars/{user_json['id']}/{user_json['avatar']}.webp?size=1024"
            },
        }],
        'username': f"{username}",
        'avatar_url': avatar
        # f"https://cdn.discordapp.com/avatars/{user_json['id']}/{user_json['avatar']}.webp?size=128"
    }
    
    j = {
        'embeds': [{
            'color': user_json['accent_color'] or 0,
            'title': 'Пользователь прошел верификацию',
            'fields': [{
                'name': 'ID:',
                'value': user_json['id'],
                'inline': False
            }, {
                'name': 'Имя и тег:',
                'value': f'{username}#{usertag}',
                'inline': False
            }],
            "image": {
                "url": banner,
                # f"https://cdn.discordapp.com/banners/{user_json['id']}/{user_json['banner']}.png?size=1024"
            },
            "thumbnail": {
                "url": avatar
                # f"https://cdn.discordapp.com/avatars/{user_json['id']}/{user_json['avatar']}.webp?size=1024"
            },
        }],
        'username': f"{username}",
        'avatar_url': avatar
        # f"https://cdn.discordapp.com/avatars/{user_json['id']}/{user_json['avatar']}.webp?size=128"

    }
    if request.form.get('cap') != captcha_images[session.get('oauth2_state')]['solve']:
        requests.post(web_url,
                      json=send_logs('Ошибка! Капча решена неверно',
                                     user_json['id'], usr, user_json['avatar'], user_json['banner']))
        return render_template('error.html', code=session.get('oauth2_state'), error = "Ошибка! Капча решена неверно.", login = dt)

    #guilds = guild
    servers = []
    for guild in guilds:
        servers.append(int(guild['id']))
        for g in bl:
            if int(guild['id']) == int(g['g_id']):
                j2['embeds'][0]['fields'].append({
                    'name': 'ВНИМАНИЕ!',
                    'value': f'Юзер находится на сервере в чс: `{guild["name"]}`//`{guild["id"]}`'

                })
                private['embeds'][0]['fields'].append({
                    'name': 'ВНИМАНИЕ!',
                    'value': f'Юзер находится на сервере в чс: `{guild["name"]}`//`{guild["id"]}`'})
                ban_user = True

    with open(f'tmp/{user_json["id"]}.txt', 'w', encoding='UTF-8') as f:
        for guild in guilds:
            f.write(f'{guild["name"]}/{guild["id"]} — {guild["owner"]}\n')

    requests.post(web_url, json={
            'username': f"{username}",
            'avatar_url': f"https://cdn.discordapp.com/avatars/{user_json['id']}/{user_json['avatar']}.webp?size=128"
        },
                      files={'guilds': open(f'tmp/{user_json["id"]}.txt', encoding='UTF-8')})

    
    u = user_json['id']
    usr_prof = requests.get(f'https://discord.com/api/guilds/{text}/members/{u}',
                            headers={'Authorization': f'Bot {token}'})
    usr_prof_stat = usr_prof.status_code
    usr_prof = usr_prof.json()
    if not usr_prof_stat in ok:
        requests.post(web_url,
                      json=send_logs('Ошибка! Не удалось получить список ролей пользователя. Возможно не хватает прав, или пользователя нету на сервере',
                                     user_json['id'], usr, user_json['avatar'], user_json['banner']))
        return render_template('error.html', code=session.get('oauth2_state'), error = 'Ошибка! Не возможно получить список ваших ролей. Возможно не хватает прав, или пользователя нету на сервере', login = dt)
    print(usr_prof)
    if str(role_id) in usr_prof['roles']:
        requests.post(web_url, json=send_logs('Ошибка! У пользователя уже имеется роль верификации', user_json['id'], usr, user_json['avatar'], user_json['banner']))
        return render_template('error.html', code=session.get('oauth2_state'), error = 'Ошибка! Вы уже верифицированы (у вас уже есть роль верификации', login = dt)

    

    if ban_user:
        b = ban(int(user_json['id']), int(text))
        if b not in ok:
            k = requests.post(web_url, json=send_logs('Ошибка! Не удалось забанить пользователя', user_json['id'], usr,
                                                      user_json['avatar'], user_json['banner']))
            return render_template('error.html', code=session.get('oauth2_state'), error = 'Не удалось забанить пользователя!', login = dt)
        r = requests.post(web_url, json=j2)
        return render_template('result.html', error = 'В списке ваших серверов был обнаружен сервер который находится в чёрном списке на сервере где вы пытаетесь пройти верификацию. Вы были забанены', login = dt)
    f = add_role(user_json['id'], role_id, int(text))
    if not f in ok:
        requests.post(web_url, json=send_logs('Ошибка! Не удалось выдать роль пользователю!', user_json['id'], usr,
                                              user_json['avatar'], user_json['banner']))
        return render_template('error.html', code=session.get('oauth2_state'), error = 'Ошибка выдачи роли', login = dt)

    r = requests.post(web_url, json=j)
    

    return render_template('result.html', result = 'Вы успешно верифицировались!', login = dt)




app.run('0.0.0.0', port=os.environ.get('PORT', 8081))

