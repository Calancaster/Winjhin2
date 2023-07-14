import os
import re
import json
import time
import ujson
import asyncio
import requests
import datetime
import winjhin.jhin as jhin
from pantheon import pantheon
from os.path import join, dirname
from dotenv import load_dotenv
from sqlalchemy import desc, update, insert, delete
from winjhin import app, db
from flask import render_template, url_for, request, redirect, session, flash
from winjhin.models import Summoner, SummonerRank, Match, MatchData

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

requests.models.complexjson = ujson

server = "na1"
api_key = os.environ.get("RIOT_API_KEY")

def requestsLog(url, status, headers):
    print(url)
    print(status)
    print(headers)

panth = pantheon.Pantheon(server, api_key, errorHandling=False, requestsLoggingFunction=requestsLog, debug=True)

async def getSummonerId(name):
    try:
        data = await panth.getSummonerByName(name)
        return (data['id'],data['accountId'],data['profileIconId'],data['summonerLevel'])
    except Exception as e:
        print(e)

async def getRecentMatchlist(accountId, begin, gameAmount):
    try:
        data = await panth.getMatchlist(accountId, params={"queue":420,"beginIndex":begin, "endIndex":gameAmount})
        return data
    except Exception as e:
        print(e)

async def getRecentMatches(accountId, gameAmount):
    try:
        matchlist = await getRecentMatchlist(accountId, gameAmount)
        tasks = [panth.getMatch(match['gameId']) for match in matchlist['matches']]
        return await asyncio.gather(*tasks)
    except Exception as e:
        print(e)

async def getRecentMatchTimelines(accountId, gameAmount):
    try:
        matchlist = await getRecentMatchlist(accountId, gameAmount)
        tasks = [panth.getTimeline(match['gameId']) for match in matchlist['matches']]
        return await asyncio.gather(*tasks)
    except Exception as e:
        print(e)

async def getDatabaseMatches(matchlist):
    try:
        tasks = [panth.getMatch(match['gameId']) for match in matchlist]
        return await asyncio.gather(*tasks)
    except Exception as e:
        print(e)    

async def getDatabaseMatchTimelines(matchlist):
    try:
        tasks = [panth.getTimeline(match['gameId']) for match in matchlist]
        return await asyncio.gather(*tasks)
    except Exception as e:
        print(e)    

loop = asyncio.get_event_loop()

@app.route('/', methods=['POST', 'GET'])
def index():

    if request.method == 'POST':

        if not request.form.get("summoner_name"):
            return render_template('apology.html', message='You must enter a valid summoner name')

        else: 
            # Getting user-inputed summoner name
            name = request.form.get("summoner_name")
            # Getting basic profile data on summoner
            (summonerId, accountId, profileIconId, summonerLevel) = loop.run_until_complete(getSummonerId(name))
            # Checking if summoner already exists in db
            check_summoner = Summoner.query.filter_by(accountId=accountId).first()
            # If the summoner is already registered, update, and move existing data as needed
            if check_summoner:
                # Removing old data from the summoner's database
                expired_matches = jhin.expireOldMatches(check_summoner.id)
                # Compare new profile data to data in db, and change as needed
                jhin.updateSummonerData(check_summoner.id, summonerId)
                # Count number of games registered under this summoner
                check_matchcount = Match.query.filter_by(summoner_id=check_summoner.id).count()
                # If less than 75 games, get most recent games played, and a few older ones, for better statistics
                if check_matchcount <= 75:
                    # Getting list of most recent matches played
                    new_matches = loop.run_until_complete(getRecentMatchlist(accountId, 0, 15))
                    new_matchList = new_matches['matches']
                    # Saving basic data from most recent matches not already in the db, and returning for use in a later function
                    games_tostore = jhin.updateSummonerMatches(check_summoner.id, new_matchList, False)
                    # Getting start and end point of older matches
                    gameSearchStart = Match.query.filter_by(summoner_id=check_summoner.id).count() - 1
                    if gameSearchStart < 0:
                        gameSearchStart = 0
                    gameAmount = gameSearchStart + 10
                    # Getting list of older matches played
                    old_matches = loop.run_until_complete(getRecentMatchlist(accountId, gameSearchStart, gameAmount))
                    old_matchList = old_matches['matches']
                    # Saving basic data from older matches not already in the db, and returning for use in a later function
                    old_games_tostore = jhin.updateSummonerMatches(check_summoner.id, old_matchList, False)
                    # Combining lists of basic data for all games not already in the db
                    games_tostore.extend(old_games_tostore)

                # If between 75 and 99 games, get only most recent games played
                elif check_matchcount < 99 and check_matchcount > 75:
                    
                    gameSearchStart = 0
                    registered_matchcount = Match.query.filter_by(summoner_id=check_summoner.id).count() - 1
                    gameAmount = 100 - registered_matchcount
                    
                    new_matches = loop.run_until_complete(getRecentMatchlist(accountId, gameSearchStart, gameAmount))
                    new_matchList = new_matches['matches']

                    games_tostore = jhin.updateSummonerMatches(check_summoner.id, new_matchList, False)

                    gameSearchStart = Match.query.filter_by(summoner_id=check_summoner.id).count() - 1
                    gameAmount = 99

                    if gameSearchStart < 99:
                        old_matches = loop.run_until_complete(getRecentMatchlist(accountId, gameSearchStart, 99))
                        old_matchList = old_matches['matches']
                        
                        old_games_tostore = jhin.updateSummonerMatches(check_summoner.id, old_matchList, False)

                        games_tostore.extend(old_games_tostore)

                # If the user has the max amount of games saved to the db
                elif check_matchcount >= 99:
                    # Setting start and end positions for finding new games
                    gameSearchStart = 0
                    gameAmount = 20
                    # Getting list of most recent games played
                    new_matches = loop.run_until_complete(getRecentMatchlist(accountId, gameSearchStart, gameAmount))
                    matchList = new_matches['matches']
                    # Saving basic match data for all matches not already in the database, and returning it for use in later function
                    games_tostore = jhin.updateSummonerMatches(check_summoner.id, matchList, True)

                # If the dict containing basic data for new games is not empty
                if games_tostore:
                    # Getting full set of match data for each new game stored in db
                    matches = loop.run_until_complete(getDatabaseMatches(games_tostore))
                    timelines = loop.run_until_complete(getDatabaseMatchTimelines(games_tostore))
                    # Deleting matches and matchdata saved more than 30 days ago, and saving new match data
                    jhin.updateSummonerMatchData(matches, timelines, accountId, check_summoner.id)

                    return redirect(url_for('summoner', name=name))

                # If the dict for new games is empty
                else:
                    return redirect(url_for('summoner', name=name))            

                return redirect(url_for('summoner', name=name))

            else:
                new_Summoner = jhin.registerSummoner(summonerId, accountId, name, profileIconId, summonerLevel)
                matchList = jhin.registerSummonerMatches(accountId, new_Summoner.id)

                if matchList:
                    matches = loop.run_until_complete(getDatabaseMatches(matchList))
                    timelines = loop.run_until_complete(getDatabaseMatchTimelines(matchList))
                
                    jhin.registerSummonerMatchData(matches, timelines, accountId, new_Summoner.id)

                    return redirect(url_for('summoner', name=name))

                else:
                    return redirect(url_for('summoner', name=name))

    elif request.method == 'GET':
        return render_template('index.html')

@app.route('/summonertest')
def summonertest():

    matchHistoryData = [
        {
            "gameDuration": {
                "minutes": 24,
                "seconds": 57
            },
            "gameTimeSince": '6 days ago',
            "outcome": 'DEFEAT',
            "teamColor": 'red',
            "gamePicks": {
                "userPlayed": 'Ryze',
                "userAgainst": 'Vladimir',
                "userTeammate1": 'Maokai',
                "userTeammate2": 'JarvanIV',
                "userTeammate3": 'Ashe',
                "userTeammate4": 'Leona',
                "userEnemy1": 'Malphite',
                "userEnemy2": 'Elise',
                "userEnemy3": 'Caitlyn',
                "userEnemy4": 'Janna'
            },
            "kills": 1,
            "deaths": 11,
            "assists": 3,
            "kda": 0.36,
            "champDmg": 3014,
            "visionScore": 22,
            "goldEarned": 6371,
            "champLevel": 13,
            "turretDmg": 0,
            "objectiveDmg": 7569,
            "creepScore": 143,
            "csPerMin": 5.7,
            "lane": 'MID',
            "summonerspells": {
                "summoner1": 'SummonerFlash',
                "summoner2": 'SummonerTeleport'
            },
            "items": {
                "item0": '3802',
                "item1": '0',
                "item2": '3003',
                "item3": '3020',
                "item4": '3089',
                "item5": '0',
                "trinket": '3363'
            },
            "runes": {
                "primarytree": ('Precision', 'perk-images/Styles/7201_Precision.png'),
                "secondarytree": ('Inspiration', 'perk-images/Styles/7203_Whimsy.png'),
                "keystone": ('LethalTempo', 'perk-images/Styles/Precision/LethalTempo/LethalTempoTemp.png'),
                "primary1": ('Triumph', 'perk-images/Styles/Precision/Triumph.png'),
                "primary2": ('LegendBloodline', 'perk-images/Styles/Precision/LegendBloodline/LegendBloodline.png'),
                "primary3": ('CoupDeGrace', 'perk-images/Styles/Precision/CoupDeGrace/CoupDeGrace.png'),
                "secondary1": ('MagicalFootwear', 'perk-images/Styles/Inspiration/MagicalFootwear/MagicalFootwear.png'),
                "secondary2": ('BiscuitDelivery', 'perk-images/Styles/Inspiration/BiscuitDelivery/BiscuitDelivery.png')
            }
        },
        {
            "gameDuration": {
                "minutes": 27,
                "seconds": 52
            },
            "gameTimeSince": '7 days ago',
            "outcome": 'DEFEAT',
            "teamColor": 'red',
            "gamePicks": {
                "userPlayed": 'Ryze',
                "userAgainst": 'Vladimir',
                "userTeammate1": 'Maokai',
                "userTeammate2": 'JarvanIV',
                "userTeammate3": 'Ashe',
                "userTeammate4": 'Leona',
                "userEnemy1": 'Malphite',
                "userEnemy2": 'Elise',
                "userEnemy3": 'Caitlyn',
                "userEnemy4": 'Janna'
            },
            "kills": 1,
            "deaths": 11,
            "assists": 3,
            "kda": 0.36,
            "champDmg": 3014,
            "visionScore": 22,
            "goldEarned": 6371,
            "champLevel": 13,
            "turretDmg": 0,
            "objectiveDmg": 7569,
            "creepScore": 143,
            "csPerMin": 5.7,
            "lane": 'TOP',
            "summonerspells": {
                "summoner1": 'SummonerFlash',
                "summoner2": 'SummonerTeleport'
            },
            "items": {
                "item0": '3802',
                "item1": '0',
                "item2": '3003',
                "item3": '3020',
                "item4": '3089',
                "item5": '0',
                "trinket": '3363'
            },
            "runes": {
                "primarytree": ('Precision', 'perk-images/Styles/7201_Precision.png'),
                "secondarytree": ('Inspiration', 'perk-images/Styles/7203_Whimsy.png'),
                "keystone": ('LethalTempo', 'perk-images/Styles/Precision/LethalTempo/LethalTempoTemp.png'),
                "primary1": ('Triumph', 'perk-images/Styles/Precision/Triumph.png'),
                "primary2": ('LegendBloodline', 'perk-images/Styles/Precision/LegendBloodline/LegendBloodline.png'),
                "primary3": ('CoupDeGrace', 'perk-images/Styles/Precision/CoupDeGrace/CoupDeGrace.png'),
                "secondary1": ('MagicalFootwear', 'perk-images/Styles/Inspiration/MagicalFootwear/MagicalFootwear.png'),
                "secondary2": ('BiscuitDelivery', 'perk-images/Styles/Inspiration/BiscuitDelivery/BiscuitDelivery.png')
            }
        },
        {
            "gameDuration": {
                "minutes": 54,
                "seconds": 23
            },
            "gameTimeSince": '8 days ago',
            "outcome": 'VICTORY',
            "teamColor": 'red',
            "gamePicks": {
                "userPlayed": 'Ryze',
                "userAgainst": 'Vladimir',
                "userTeammate1": 'Maokai',
                "userTeammate2": 'JarvanIV',
                "userTeammate3": 'Ashe',
                "userTeammate4": 'Leona',
                "userEnemy1": 'Malphite',
                "userEnemy2": 'Elise',
                "userEnemy3": 'Caitlyn',
                "userEnemy4": 'Janna'
            },
            "kills": 1,
            "deaths": 11,
            "assists": 3,
            "kda": 0.36,
            "champDmg": 3014,
            "visionScore": 22,
            "goldEarned": 6371,
            "champLevel": 13,
            "turretDmg": 0,
            "objectiveDmg": 7569,
            "creepScore": 143,
            "csPerMin": 5.7,
            "lane": 'TOP',
            "summonerspells": {
                "summoner1": 'SummonerFlash',
                "summoner2": 'SummonerTeleport'
            },
            "items": {
                "item0": '3802',
                "item1": '0',
                "item2": '3003',
                "item3": '3020',
                "item4": '3089',
                "item5": '0',
                "trinket": '3363'
            },
            "runes": {
                "primarytree": ('Precision', 'perk-images/Styles/7201_Precision.png'),
                "secondarytree": ('Inspiration', 'perk-images/Styles/7203_Whimsy.png'),
                "keystone": ('LethalTempo', 'perk-images/Styles/Precision/LethalTempo/LethalTempoTemp.png'),
                "primary1": ('Triumph', 'perk-images/Styles/Precision/Triumph.png'),
                "primary2": ('LegendBloodline', 'perk-images/Styles/Precision/LegendBloodline/LegendBloodline.png'),
                "primary3": ('CoupDeGrace', 'perk-images/Styles/Precision/CoupDeGrace/CoupDeGrace.png'),
                "secondary1": ('MagicalFootwear', 'perk-images/Styles/Inspiration/MagicalFootwear/MagicalFootwear.png'),
                "secondary2": ('BiscuitDelivery', 'perk-images/Styles/Inspiration/BiscuitDelivery/BiscuitDelivery.png')
            }
        }
    ]

    return render_template('summonertest.html', matchHistoryData=matchHistoryData)

@app.route('/summoner/<name>')
def summoner(name):

    # Checking if the json for post-game tag descriptions exists. If not, make it. If so, open it
    if not os.path.isfile("winjhin/tooltip_json/tag_descriptions.json") or os.stat("winjhin/tooltip_json/tag_descriptions.json").st_size == 0:
        f = open("winjhin/tooltip_json/tag_descriptions.json", "w")
        virtue = 'I have risen from the filth and muck. I am the lotus blossom. I...am beauty.'
        tag_descriptions = {
            "Virtuoso": f'"{virtue}" This game you were the performer, the carry. Your momentum to get the win was created from the pressure you exerted to the map, and from your unwavered farming efficiency.',
            "Win Streak": "You're on a win streak, keep up the good work!",
            "Fighter": "Despite this game being a loss, you were still proactive. Your kill participation indicates you were actively looking for plays to swing the game back into your favor.",
            "On Fire": "Recently, you have maintained a high winrate, and have been performing admirably. Even if you lose one or two, just reset and keep up the good work.",
            "Good Farming": "You maintained an efficient income of gold and xp from minions this game.",
            "Untouchable": "Your KDA this game was well-beyond average for your role.",
            "Unlucky": "You performed very well in this match, but a small percentage of games are simply out of your control. Even the best players have a limit to how hard they can carry.",
            "Good KDA": "You were able to find a good number of takedowns, without sacrificing yourself in the process. Well done.",
            "Ever-present": "Very little happened on the map without you there. Your high kill participation was a huge part of this win.",
            "Sightstone": "You placed an amount of wards that is above what is typically expected of your role. Well done.",
            "All-Seeing": "You had complete control of the map when it comes to vision, coming in well above what is typically expected from your role in wards placed, wards destroyed, and control wards placed.",
            "Inefficient": "Despite this game being a win, there was a considerable amount of gold and xp you could have gotten in the process. Make sure to take advantage of every available resource when ahead to maximize your chances of winning.",
            "Starving": "There was a considerable amount of gold and xp that was lost in farm this game. If you aren't strong enough to pressure your opponent directly, try to focus your attention on minions and monsters to minimize your deficit.",
            "Viewer": "You participated in less takedowns than what was desired from you this game.",
            "Break Time": "This game was played during a spree of losses and/or poor performances. Make sure to take frequent breaks to reset your mind.",
            "Zombie": "You had a considerable amount of deaths this game.",
            "Dark Map": "You placed less wards than what would typically be expected of your role this game.",
            "Bad Control": "Either your placement of control wards or your removal of enemy vision was somewhat lacking this game.",
            "No Control": "You did not disrupt enough of the enemy's vision this game. Control wards are some of the most efficient items in the game, make sure to pick up a few every game."
        }
        json.dump(tag_descriptions, f)
    else:
        f = open('winjhin/tooltip_json/tag_descriptions.json')
        tag_descriptions = json.load(f)
    f.close()
    # Checking if the json for item names exists. If not, make it. If so, open it
    if not os.path.isfile("winjhin/tooltip_json/item_names.json") or os.stat("winjhin/tooltip_json/item_names.json").st_size == 0:
        g = open("winjhin/tooltip_json/item_names.json", "w")
        item_names = {
            "1001": "Boots of Speed",
            "1004": "Faerie Charm",
            "1006": "Rejuvenation Bead",
            "1011": "Giant's Belt",
            "1018": "Cloak of Agility",
            "1026": "Blasting Wand",
            "1027": "Sapphire Crystal",
            "1028": "Ruby Crystal",
            "1029": "Cloth Armor",
            "1031": "Chain Vest",
            "1033": "Null-Magic Mantle",
            "1035": "Emberknife",
            "1036": "Long Sword",
            "1037": "Pickaxe",
            "1038": "BF Sword",
            "1039": "Hailblade",
            "1042": "Dagger",
            "1043": "Recurve Bow",
            "1052": "Amplifying Tome",
            "1053": "Vampiric Scepter",
            "1054": "Doran's Shield",
            "1055": "Doran's Blade",
            "1056": "Doran's Ring",
            "1057": "Negatron Cloak",
            "1058": "Needlessly Large Rod",
            "1082": "Dark Seal",
            "1083": "Cull",
            "2003": "Health Potion",
            "2010": "Total Biscuit of Everlasting Will",
            "2015": "Kircheis Shard",
            "2031": "Refillable Potion",
            "2033": "Corrupting Potion",
            "2051": "Guardian's Horn",
            "2055": "Control Ward",
            "2065": "Shurlya's Battlesong",
            "2138": "Elixar of Iron",
            "2139": "Elixar of Sorcery",
            "2140": "Elixar of Wrath",
            "2403": "Minion Dematerializer",
            "2419": "Commencing Stopwatch",
            "2420": "Perfectly Timed Stopwatch",
            "2421": "Broken Stopwatch",
            "2422": "Slightly Magical Boots",
            "2423": "Stopwatch",
            "2424": "Broken Stopwatch",
            "3001": "Abyssal Mask",
            "3003": "Archangel's Staff",
            "3004": "Manamune",
            "3006": "Berserker's Greaves",
            "3009": "Boots of Swiftness",
            "3011": "Chemtech Putrifier",
            "3020": "Sorcerer's Shoes",
            "3024": "Glacial Buckler",
            "3026": "Guardian Angel",
            "3031": "Infinity Edge",
            "3033": "Mortal Reminder",
            "3035": "Last Whisper",
            "3036": "Lord Dominik's Regard",
            "3040": "Seraph's Embrace",
            "3041": "Mejai's Soulstealer",
            "3042": "Muramana",
            "3043": "Muramana",
            "3044": "Phage",
            "3046": "Phantom Dancer",
            "3047": "Plated Steelcaps",
            "3048": "Seraph's Embrace",
            "3050": "Zeke's Convergence",
            "3051": "Hearthbound Axe",
            "3053": "Sterak's Gage",
            "3057": "Sheen",
            "3065": "Spirit Visage",
            "3066": "Winged Moonplate",
            "3067": "Kindlegem",
            "3068": "Sunfire Aegis",
            "3070": "Tear of the Goddess",
            "3071": "Black Cleaver",
            "3072": "Bloodthirster",
            "3074": "Ravenous Hydra",
            "3075": "Thornmail",
            "3076": "Bramble Vest",
            "3077": "Tiamat",
            "3078": "Trinity Force",
            "3082": "Warden's Mail",
            "3083": "Warmog's Armor",
            "3085": "Runaan's Hurricane",
            "3086": "Zeal",
            "3089": "Rabadon's Deathcap",
            "3091": "Wit's End",
            "3094": "Rapidfire Cannon",
            "3095": "Stormrazor",
            "3100": "Lich Bane",
            "3102": "Banshee's Veil",
            "3105": "Aegis of the Legion",
            "3107": "Redemption",
            "3108": "Fiendish Codex",
            "3109": "Knight's Vow",
            "3110": "Frozen Heart",
            "3111": "Mercury Treads",
            "3112": "Guardian's Orb",
            "3113": "Aether Wisp",
            "3114": "Forbidden Idol",
            "3115": "Nashor's Tooth",
            "3116": "Rylai's Crystal Scepter",
            "3117": "Mobility Boots",
            "3123": "Executioner's Calling",
            "3124": "Guinsoo's Rageblade",
            "3133": "Caulfield's Warhammer",
            "3134": "Serrated Dirk",
            "3135": "Void Staff",
            "3139": "Mercurial Scimitar",
            "3140": "Quicksilver Sash",
            "3142": "Youmuu's Ghostblade",
            "3143": "Randuin's Omen",
            "3145": "Hextech Alternator",
            "3152": "Hextech Rocketbelt",
            "3153": "Blade of the Ruined King",
            "3155": "Hexdrinker",
            "3156": "Maw of Malmortius",
            "3157": "Zhonya's Hourglass",
            "3158": "Ionian Boots of Lucidity",
            "3165": "Morellonomicon",
            "3177": "Guardian's Blade",
            "3179": "Umbral Glaive",
            "3181": "Sanguine Blade",
            "3184": "Guardian's Hammer",
            "3190": "Locket of the Iron Solari",
            "3191": "Seeker's Armguard",
            "3193": "Gargoyle's Stoneplate",
            "3211": "Spectre's Cowl",
            "3222": "Mikael's Blessing",
            "3330": "Scarecrow Effigy",
            "3340": "Stealth Ward",
            "3363": "Farsight Alteration",
            "3364": "Oracle's Lens",
            "3400": "Your Cut",
            "3504": "Ardent Censor",
            "3508": "Essence Reaver",
            "3513": "Eye of the Herald",
            "3599": "Black Spear",
            "3600": "Black Spear",
            "3742": "Dead Man's Plate",
            "3748": "Titanic Hydra",
            "3801": "Crystalline Bracer",
            "3802": "Lost Chapter",
            "3814": "Edge of Night",
            "3850": "Spellthief's Edge",
            "3851": "Frostfang",
            "3853": "Shard of True Ice",
            "3854": "Steel Shoulderguards",
            "3855": "Runesteel Spaulders",
            "3857": "Pauldron's of Whiterock",
            "3858": "Relic Shield",
            "3859": "Targon's Buckler",
            "3860": "Bulwark of the Mountain",
            "3862": "Spectral Sickle",
            "3863": "Harrowing Crescent",
            "3864": "Black Mist Scythe",
            "3916": "Oblivion Orb",
            "4005": "Imperial Mandate",
            "4401": "Force of Nature",
            "4403": "Urf's Spatula",
            "4628": "Horizon Focus",
            "4629": "Cosmic Drive",
            "4630": "Blighting Jewel",
            "4632": "Verdant Barrier",
            "4633": "Riftmaker",
            "4635": "Leeching Leer",
            "4636": "Night Harvester",
            "4637": "Demonic Embrace",
            "4638": "Watchful Wardstone",
            "4641": "Stirring Wardstone",
            "4642": "Bandleglass Mirror",
            "4643": "Vigilant Wardstone",
            "6029": "Ironspike Whip",
            "6035": "Silvermere Dawn",
            "6333": "Death's Dance",
            "6609": "Chempunk Chainsword",
            "6616": "Staff of Flowing Water",
            "6617": "Moonstone Renewer",
            "6630": "Goredrinker",
            "6631": "Stridebreaker",
            "6632": "Divine Sunderer",
            "6653": "Liandry's Anguish",
            "6655": "Luden's Tempest",
            "6656": "Everfrost",
            "6660": "Bami's Cinder",
            "6662": "Frostfire Gauntlet",
            "6664": "Turbo Chemtank",
            "6670": "Noonquiver",
            "6671": "Galeforece",
            "6672": "Kraken Slayer",
            "6673": "Immortal Shieldbow",
            "6675": "Navori Quickblades",
            "6676": "The Collector",
            "6677": "Serylda's Grudge",
            "6691": "Duskblade of Draktharr",
            "6692": "Eclipse",
            "6693": "Prowler's Claw",
            "6694": "Rageknife",
            "6695": "Serpent's Fang"
        }
        json.dump(item_names, g)
    else:
        g = open("winjhin/tooltip_json/item_names.json")
        item_names = json.load(g)
    g.close()
    # Checking if the json for summoner spell names exists. If not, make it. If so, open it
    if not os.path.isfile("winjhin/tooltip_json/ss_names.json") or os.stat("winjhin/tooltip_json/ss_names.json").st_size == 0:
        h = open("winjhin/tooltip_json/ss_names.json", "w")
        ss_names = {
            "SummonerBarrier": "Barrier",
            "SummonerBoost": "Cleanse",
            "SummonerDot": "Ignite",
            "SummonerExhaust": "Exhaust",
            "SummonerFlash": "Flash",
            "SummonerHaste": "Ghost",
            "SummonerHeal": "Heal",
            "SummonerMana": "Clarity",
            "SummonerSmite": "Smite",
            "SummonerTeleport": "Teleport"
        }
    else:
        h = open("winjhin/tooltip_json/ss_names.json")
        ss_names = json.load(h)
    h.close()
    # Getting basic summoner data, and encrypted IDs for the summoner
    (summonerId, accountId, profileIconId, summonerLevel) = loop.run_until_complete(getSummonerId(name))
    # Getting whatever summoner data is currently stored in the database
    this_summoner = Summoner.query.filter_by(name=name).first()
    summoner_id = this_summoner.id
    # Getting matchlist from this summoner that are stored in the database
    matchList_raw = Match.query.filter_by(summoner_id=this_summoner.id).order_by(desc(Match.timestamp)).all()
    matchList = []
    for match in matchList_raw:
        this_match = {
            'Id': match.id,
            'gameId': match.gameId,
            'champion': match.champion,
            'timestamp': match.timestamp,
            'date_saved': match.date_saved,
            'summoner_id': match.summoner_id
        }
        matchList.append(this_match)
    # Determining the amount of matches to check for full data
    gameAmount = Match.query.filter_by(summoner_id=this_summoner.id).count()
    matchList = matchList[:gameAmount]
    # Unpacking and sorting necessary match data from the database for this summoner 
    (matchHistoryData, championDict, championList) = jhin.unpackMatchData(matchList)
    top5Champions = championList[:5]
    # Sorting the user's top 5 champions based on data above
    statsOnTop5 = jhin.unpackTop5(top5Champions, matchHistoryData)
    # Sorting the user's basic stats on each role based on the data above
    roleStats = jhin.unpackRoleStats(matchHistoryData)
    # Getting advanced summoner data from the database (Rank information)
    summoner_SummonerRank = SummonerRank.query.filter_by(summoner_id=this_summoner.id).first()
    while summoner_SummonerRank:
        summoner_info = {
            "profileIconId": str(profileIconId),
            "summonerLevel": summonerLevel,
            "name": this_summoner.name,
            "tier": summoner_SummonerRank.tier,
            "rank": summoner_SummonerRank.division,
            "lp": summoner_SummonerRank.leaguePoints,
            "wins": summoner_SummonerRank.wins,
            "losses": summoner_SummonerRank.losses,
            "totalGames": summoner_SummonerRank.wins + summoner_SummonerRank.losses
        }
        break
    summoner_info['winrate'] = round((summoner_info['wins'] / summoner_info['totalGames']) * 100, 2)
    # Cutting all but the last 20 games from the list of full matches
    matchHistoryData = matchHistoryData[:20]
    # Getting champion stats for the last 20 games played
    matchList = matchList[:21]
    (last20matchHistoryData, last20championDict, last20championList) = jhin.unpackMatchData(matchList)
    last20top5Champions = last20championList[:5]
    last20statsOnTop5 = jhin.unpackTop5(last20top5Champions, last20matchHistoryData)
    # Getting post-game tags for any games that will be shown on the summoner page
    summoner_tags = jhin.getSingleGameTags(matchHistoryData)    

    return render_template('summoner.html', summoner_info=summoner_info, matchHistoryData=matchHistoryData, name=name, championList=championList,
                                            championDict=championDict, statsOnTop5=statsOnTop5, roleStats=roleStats,last20Dict=last20championDict,
                                            last20List=last20championList, last20Top5=last20statsOnTop5, summoner_tags=summoner_tags,
                                            tag_descriptions=tag_descriptions, item_names=item_names, ss_names=ss_names)
