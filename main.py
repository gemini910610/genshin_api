import requests
import time
import random
import string
import hashlib
import json

with open('./data.json', 'r') as file:
    data = json.load(file)
    ACT_ID = data['ACT_ID']
    LTUID = data['LTUID']
    LTOKEN = data['LTOKEN']
    COOKIE_TOKEN = data['COOKIE_TOKEN']
    HOYOLAB_ACCOUNT_ID = data['HOYOLAB_ACCOUNT_ID']
    ROLE_ID = data['ROLE_ID']

class Genshin:
    ACT_ID = ACT_ID
    DS_SALT = '6cqshh5dhw73bzxn20oexa9k516chk7s'

    def __init__(self, **args):
        self.ltuid = args.get('ltuid', '')
        self.ltoken = args.get('ltoken', '')
        self.cookie_token = args.get('cookie_token', '')
        self.hoyolab_account_id = args.get('hoyolab_account_id', '')
        self.language = args.get('language', '')

    def request_hk4e(self, endpoint: str, method: str = 'get') -> dict:
        url = f'https://hk4e-api-os.hoyoverse.com/event/sol/{endpoint}'
        headers = {'cookie': f'ltuid={self.ltuid}; ltoken={self.ltoken};'}
        parameters = {'act_id': self.ACT_ID, 'lang': self.language}
        return requests.request(method, url, headers=headers, params=parameters).json()

    def sign(self) -> str:
        # success = {'retcode': 0, 'message': 'OK', 'data': {'code': 'ok'}}
        # already = {'data': None, 'message': '旅行者，你已經簽到過了~', 'retcode': -5003}
        response = self.request_hk4e('sign', 'post')
        if response['retcode'] == 0:
            return '簽到成功'
        else:
            return response['message']

    def sign_award(self) -> list[dict]:
        response = self.request_hk4e('award')['data']['list']
        days = len(response)
        awards: list[dict] = [0] * days
        for day in range(days):
            award = response[day]
            item = award['name']
            count = award['cnt']
            time = award['created_at'][:10]
            # image = award['img']
            awards[day] = {'item': item, 'count': count, 'time': time}
        return awards

    def sign_info(self) -> dict:
        response = self.request_hk4e('info')['data']
        count = response['total_sign_day']
        today = response['today']
        sign = response['is_sign']
        return {'count': count, 'today': today, 'signed': sign}

    def sign_month_award(self) -> tuple[int, list[dict]]:
        response = self.request_hk4e('home')['data']
        month = response['month']
        month_awards = response['awards']
        days = len(month_awards)
        awards: list[dict] = [0] * days
        for day in range(days):
            award = month_awards[day]
            item = award['name']
            count = award['cnt']
            # image = award['icon']
            awards[day] = {'item': item, 'count': count}
        return (month, awards)

    def generate_ds(self) -> str:
        t = int(time.time())
        r = ''.join(random.choices(string.ascii_letters, k=6))
        h = hashlib.md5(f'salt={self.DS_SALT}&t={t}&r={r}'.encode()).hexdigest()
        return f'{t},{r},{h}'

    def request_bbs(self, endpoint: str, parameters: dict, method: str = 'get') -> dict:
        url = f'https://bbs-api-os.hoyolab.com/game_record/{endpoint}'
        headers = {
            'cookie': f'ltuid={self.ltuid}; ltoken={self.ltoken};',
            'ds': self.generate_ds(),
            'x-rpc-app_version': '1.5.0',
            'x-rpc-client_type': '4',
            'x-rpc-language': self.language,
        }
        return requests.request(method, url, headers=headers, params=parameters).json()

    def get_games(self) -> dict:
        url = 'https://bbs-api-os.hoyolab.com/community/misc/wapi/business'
        headers = {'x-rpc-language': 'zh-tw'}
        response = requests.get(url, headers=headers).json()['data']['business']
        games = {}
        for game in response:
            id = game['id']
            name = game['name']
            image = game['icon']
            games[str(id)] = {'name': name, 'image': image}
        return games

    def get_roles(self) -> list[dict]:
        parameters = {'uid': self.hoyolab_account_id}
        response = self.request_bbs('card/wapi/getGameRecordCard', parameters)['data'][
            'list'
        ]
        count = len(response)
        roles: list[dict] = [0] * count
        games = self.get_games()
        for index in range(count):
            role = response[index]
            # has_role = role['has_role']
            game_id = role['game_id']
            game_role_id = role['game_role_id']
            nickname = role['nickname']
            region = role['region']
            level = role['level']
            data = role['data']
            region_name = role['region_name']
            datum = {}
            for d in data:
                datum[d['name']] = d['value']
            roles[index] = {
                'game': games[str(game_id)]['name'],
                'role_id': game_role_id,
                'role_name': nickname,
                'level': level,
                'region': region,
                'region_name': region_name,
                'data': datum,
            }
        return roles

    def get_role_info(self, role_id: str, region: str) -> dict:
        parameters = {'role_id': role_id, 'server': region}
        response = self.request_bbs('genshin/api/index', parameters)['data']
        data = {}

        role = response['role']
        data['role'] = {'name': role['nickname'], 'level': role['level']}

        data['stats'] = response['stats']
        data['city'] = response['city_explorations']

        world = response['world_explorations']
        count = len(world)
        areas: list[dict] = [0] * count
        for index in range(count):
            area = world[index]
            offerings = area['offerings']
            offering_count = len(offerings)
            offering: list[dict] = [0] * offering_count
            for index in range(offering_count):
                offer = offerings[index]
                offering[index] = {
                    'name': offer['name'],
                    'level': offer['level'],
                    # 'icon': offer['icon'] # if use this, don't need to process offerings data
                }
            areas[index] = {
                'name': area['name'],
                'level': area['level'],
                'exploration_percentage': area['exploration_percentage'],
                'offerings': offering,
                # 'icon': area['icon'],
                # 'inner_icon': area['inner_icon']
            }
        data['world'] = areas

        return data

    def get_character(self, role_id: str, region: str) -> list[dict]:
        parameters = {'role_id': role_id, 'server': region}
        response = self.request_bbs('genshin/api/character', parameters, 'post')[
            'data'
        ]['avatars']
        count = len(response)
        characters: list[dict] = [0] * count
        for index in range(count):
            character = response[index]

            weapon = character['weapon']
            weapon_data = {
                'name': weapon['name'],
                'rarity': weapon['rarity'],
                'type': weapon['type_name'],
                'level': weapon['level'],
                'promote_level': weapon['promote_level'],
                'affix_level': weapon['affix_level'],
                'description': weapon['desc'],
                # 'image': weapon['icon']
            }

            reliquaries = character['reliquaries']
            reliquary_count = len(reliquaries)
            reliquary_list: list[dict] = [0] * reliquary_count
            for reliquary_index in range(reliquary_count):
                reliquary = reliquaries[reliquary_index]
                reliquary_set = reliquary['set']
                reliquary_list[reliquary_index] = {
                    'name': reliquary['name'],
                    'rarity': reliquary['rarity'],
                    'pos': reliquary['pos_name'],
                    'level': reliquary['level'],
                    'set': {
                        'name': reliquary_set['name'],
                        'affixes': reliquary_set['affixes'],
                    },
                }

            constellations = character['constellations']
            constellation_count = len(constellations)
            constellation_list: list[dict] = [0] * constellation_count
            for constellation_index in range(constellation_count):
                constellation = constellations[constellation_index]
                constellation_list[constellation_index] = {
                    'name': constellation['name'],
                    'effect': constellation['effect'],
                    'is_actived': constellation['is_actived'],
                    # 'image': constellation['icon']
                }

            costumes = character['costumes']
            costume_count = len(costumes)
            costume_list: list[dict] = [0] * costume_count
            for costume_index in range(costume_count):
                costume = costumes[costume_index]
                costume_list[costume_index] = {
                    'name': costume['name'],
                    # 'image': costume['icon']
                }

            characters[index] = {
                'name': character['name'],
                'rarity': character['rarity'],
                'element': character['element'],
                'level': character['level'],
                'actived_constellation_num': character['actived_constellation_num'],
                'weapon': weapon_data,
                'reliquaries': reliquary_list,
                'constellations': constellation_list,
                'costumes': costume_list,
                'fetter': character['fetter'],
                # 'image': character['image'],
                # 'icon': character['icon']
            }
        return characters

    def get_card_info(self, role_id: str, region: str) -> dict:
        parameters = {'role_id': role_id, 'server': region}
        response = self.request_bbs('genshin/api/gcg/basicInfo', parameters)['data']
        return {
            'name': response['nickname'],
            'level': response['level'],
            'character_card_gained': response['avatar_card_num_gained'],
            'character_card_total': response['avatar_card_num_total'],
            'action_card_gained': response['action_card_num_gained'],
            'action_card_total': response['action_card_num_total'],
        }

    def get_card_list(self, role_id: str, region: str, **parameters) -> list[dict]:
        # parameters = {
        #     'need_avatar': 'true',
        #     'need_action': 'true',
        #     'limit': 32,
        # }
        parameters['role_id'] = role_id
        parameters['server'] = region
        parameters['offset'] = 0
        return self.request_bbs('genshin/api/gcg/cardList', parameters)['data']['card_list']

    def get_character_card(self, role_id: str, region: str) -> list[dict]:
        count = self.get_card_info(role_id, region)['character_card_total']
        response = self.get_card_list(role_id, region, need_avatar='true', limit=count)
        characters: list[dict] = [0] * count
        for index in range(count):
            character = response[index]
            skills = character['card_skills']
            skill_dict = {}
            for skill in skills:
                skill_dict[skill['tag']] = {
                    'name': skill['name'],
                    'description': skill['desc']
                }
            characters[index] = {
                'name': character['name'],
                'hp': character['hp'],
                'proficiency': character['proficiency'],
                'use_count': character['use_count'],
                'skills': skill_dict,
                'num': character['num'],
                # 'image': character['image'],
                # 'tags': character['tags']
            }
        return characters

    def get_action_card(self, role_id: str, region: str) -> list[dict]:
        count = self.get_card_info(role_id, region)['action_card_total'] // 2
        response = self.get_card_list(role_id, region, need_action='true', limit=count)
        actions: list[dict] = [0] * count
        for index in range(count):
            action = response[index]
            actions[index] = {
                'name': action['name'],
                'card_type': action['card_type'],
                'action_cost': action['action_cost'],
                'description': action['desc'],
                'use_count': action['use_count'],
                'num': action['num'],
                # 'image': action['image']
            }
        return actions

    def get_card_back(self, role_id: str, region: str):
        parameters = {'role_id': role_id, 'server': region}
        response = self.request_bbs('genshin/api/gcg/cardBackList', parameters)['data']['card_back_list']
        count = len(response)
        backs: list[dict] = [0] * count
        for index in range(count):
            back = response[index]
            backs[index] = {
                'image': back['image'],
                'has_obtained': back['has_obtained']
            }
        return backs

    '''
    def get_spiral(self, role_id, region, schedule_type) -> dict:
        # schedule_type: 1 current, 2 previous
        parameters = {
            'role_id': role_id,
            'server': region,
            'schedule_type': schedule_type,
        }
        return self.request_bbs('genshin/api/spiralAbyss', parameters)['data']
    '''

    '''
    def get_note(self, role_id, region) -> dict:
        parameters = {'role_id': role_id, 'server': region}
        return self.request_bbs('genshin/api/dailyNote', parameters)['data']
    '''

    '''
    def get_game_role(self):
        url = 'https://api-os-takumi.hoyoverse.com/binding/api/getUserGameRolesByCookie'
        headers = {'cookie': f'ltuid={self.ltuid}; ltoken={self.ltoken};'}
        return requests.get(url, headers=headers).json()
    '''

    def redeem_code(self, role_id, region, code):
        url = 'https://sg-hk4e-api.hoyoverse.com/common/apicdkey/api/webExchangeCdkey'
        headers = {
            'cookie': f'cookie_token={self.cookie_token}; account_id={self.ltuid};'
        }
        parameters = {
            'uid': role_id,
            'region': region,
            'cdkey': code,
            'lang': self.language,
            'game_biz': 'hk4e_global',
        }
        return requests.get(url, headers=headers, params=parameters).json()['message']


genshin = Genshin(
    ltuid=LTUID,
    ltoken=LTOKEN,
    cookie_token=COOKIE_TOKEN,
    hoyolab_account_id=HOYOLAB_ACCOUNT_ID,
    language='zh-tw',
)
role_id = ROLE_ID
region = 'os_cht'
print(genshin.get_role_info(role_id, region))
