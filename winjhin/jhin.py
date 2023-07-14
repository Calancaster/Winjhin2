import requests
import json
import ujson
import os
import asyncio
import datetime
import math
import time
import re
import roleml
from dateutil import relativedelta
from os.path import join, dirname
from dotenv import load_dotenv
from winjhin import app, db
from pantheon import pantheon
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

asyncio.set_event_loop(asyncio.SelectorEventLoop())
panth = pantheon.Pantheon(server, api_key, errorHandling=False, requestsLoggingFunction=requestsLog, debug=True)

async def getSummonerInfo(summonerId):
    try:
        data = await panth.getLeaguePosition(summonerId)
        return data
    except Exception as e:
        print(e)   

async def getRecentMatchlist(accountId, begin, gameAmount):
    try:
        data = await panth.getMatchlist(accountId, params={"queue":420, "beginIndex":begin, "endIndex":gameAmount})
        return data
    except Exception as e:
        print(e)

loop = asyncio.get_event_loop()

def merge(matches, timelines):

    merged_list = [(matches[i], timelines[i]) for i in range(0, len(matches))]
    return merged_list

def convertTime(game_length):
    time = game_length
    minutes = time // 60
    time %= 60
    seconds = time
    convertedTime = {
        "minutes": int(minutes),
        "seconds": int(seconds)
    }
    return convertedTime

def getTimeSince(game_date):
    time_now = time.time()
    time_now = datetime.datetime.fromtimestamp(time_now)
    game_date = datetime.datetime.fromtimestamp(game_date)

    time_between = relativedelta.relativedelta(time_now, game_date)

    if int(time_between.months) >= 1:
        timeBetween = "%i month(s) ago"%time_between.months
        return timeBetween
    elif int(time_between.months) <= 1 and int(time_between.days) >= 1:
        timeBetween = "%i day(s) ago"%time_between.days
        return timeBetween
    elif int(time_between.months) <= 1 and int(time_between.days) <= 1 and int(time_between.hours) >= 1:
        timeBetween = "%i hour(s) ago"%time_between.hours
        return timeBetween
    else:
        timeBetween = "%i minutes ago"%time_between.minutes       
        return timeBetween

def getChampion(championId):
    
    Champion = None

    if championId <= 0:
        Champion = 'notInteger'

    else:
        with open(r"winjhin\static\dragontail-11.7.1\11.7.1\data\en_US\champion.json", "r", encoding="utf8") as champions_json:
            champions_decoded = json.load(champions_json)
            champions_data = champions_decoded['data']

            for champ in champions_data.keys():
                thisChamp = champions_data[champ]
                thisChampKey = thisChamp['key']

                if int(thisChampKey) == championId:
                    Champion = re.sub('[\W_]', '', thisChamp['name'])
                    break
                
    return Champion 

def getUserBuild(participant):

    UserSummoners = {}

    with open(r"winjhin\static\dragontail-11.7.1\11.7.1\data\en_US\summoner.json", "r", encoding="utf8") as summoners_json:
        summoners_decoded = json.load(summoners_json)
        summoners_data = summoners_decoded['data']

        for summonerSpell in summoners_data.keys():
            thisSummonerSpell = summoners_data[summonerSpell]
            thisSummonerSpellKey = thisSummonerSpell['key']

            if int(thisSummonerSpellKey) == int(participant['spell1Id']):
                UserSummoners['summoner1'] = thisSummonerSpell['id']
                continue
            elif int(thisSummonerSpellKey) == int(participant['spell2Id']):
                UserSummoners['summoner2'] = thisSummonerSpell['id']
                continue
    
    userStats = participant['stats']
    UserItems = {
        "item0": userStats['item0'],
        "item1": userStats['item1'],
        "item2": userStats['item2'],
        "item3": userStats['item3'],
        "item4": userStats['item4'],
        "item5": userStats['item5'],
        "trinket": userStats['item6']
    }

    UserRunesIds = {
        "primarytree": userStats['perkPrimaryStyle'],
        "secondarytree": userStats['perkSubStyle'],
        "keystone": userStats['perk0'],
        "primary1": userStats['perk1'],
        "primary2": userStats['perk2'],
        "primary3": userStats['perk3'],
        "secondary1": userStats['perk4'],
        "secondary2": userStats['perk5']
    }
    UserRunes = {
        "primarytree": (None, None),
        "secondarytree": (None, None),
        "keystone": (None, None),
        "primary1": (None, None),
        "primary2": (None, None),
        "primary3": (None, None),
        "secondary1": (None, None),
        "secondary2": (None, None)
    }

    with open(r"winjhin\static\dragontail-11.7.1\11.7.1\data\en_US\runesReforged.json", "r", encoding="utf8") as runes_json:
        runes_decoded = json.load(runes_json)
        
        for tree in runes_decoded:
            if tree['id'] == UserRunesIds['primarytree']:
                UserRunes['primarytree'] = (tree['key'], tree['icon'])
                primarytree_keystones = tree['slots'][0]['runes']
                primarytree_slot1 = tree['slots'][1]['runes']
                primarytree_slot2 = tree['slots'][2]['runes']
                primarytree_slot3 = tree['slots'][3]['runes']

                for keystone in primarytree_keystones:
                    if keystone['id'] == UserRunesIds['keystone']:
                        UserRunes['keystone'] = (keystone['key'], keystone['icon'])
                
                for rune in primarytree_slot1:
                    if rune['id'] == UserRunesIds['primary1']:
                        UserRunes['primary1'] = (rune['key'], rune['icon'])

                for rune in primarytree_slot2:
                    if rune['id'] == UserRunesIds['primary2']:
                        UserRunes['primary2'] = (rune['key'], rune['icon'])

                for rune in primarytree_slot3:
                    if rune['id'] == UserRunesIds['primary3']:
                        UserRunes['primary3'] = (rune['key'], rune['icon'])

            elif tree['id'] == UserRunesIds['secondarytree']:
                UserRunes['secondarytree'] = (tree['key'], tree['icon'])
                secondarytree_slot1 = tree['slots'][1]['runes']
                secondarytree_slot2 = tree['slots'][2]['runes']
                secondarytree_slot3 = tree['slots'][3]['runes']

                for rune in secondarytree_slot1:
                    if rune['id'] == UserRunesIds['secondary1']:
                        UserRunes['secondary1'] = (rune['key'], rune['icon'])

                for rune in secondarytree_slot2:
                    if rune['id'] == UserRunesIds['secondary1']:
                        UserRunes['secondary1'] = (rune['key'], rune['icon'])
                    elif rune['id'] == UserRunesIds['secondary2']:
                        UserRunes['secondary2'] = (rune['key'], rune['icon'])

                for rune in secondarytree_slot3:
                    if rune['id'] == UserRunesIds['secondary2']:
                        UserRunes['secondary2'] = (rune['key'], rune['icon'])        

    UserBuild = {
        "summonerspells": UserSummoners,
        "items": UserItems,
        "runes": UserRunes
    }

    return UserBuild

def getChampionsPlayed(matchList):

    championsPlayedBefore = {}
    championsPlayedAfter = {}

    for match in matchList['matches']:

        userChampId = match['champion']

        if userChampId in championsPlayedBefore.keys():
            championsPlayedBefore[userChampId] += 1

        else:
            championsPlayedBefore[userChampId] = 1

    with open(r"winjhin\static\dragontail-11.7.1\11.7.1\data\en_US\champion.json", "r", encoding="utf8") as champions_json:
        champions_decoded = json.load(champions_json)
        champions_data = champions_decoded['data']

        for champPlayedId in championsPlayedBefore:

            for champ in champions_data.keys():
                    thisChamp = champions_data[champ]
                    thisChampKey = thisChamp['key']

                    if thisChampKey == str(champPlayedId):
                        identifiedChamp = re.sub('[\W_]+', '', thisChamp['name'])
                        championsPlayedAfter[identifiedChamp] = championsPlayedBefore[champPlayedId]
                        break

    championsPlayedIds = {k: v for k, v in sorted(championsPlayedBefore.items(), key=lambda item: item[1], reverse=True)}
    championsPlayedNames = {k: v for k, v in sorted(championsPlayedAfter.items(), key=lambda item: item[1], reverse=True)}

    return (championsPlayedIds, championsPlayedNames)

def getRoleDistribution(matchList):

    roleDistribution = {
        "top": {
            "roleName": 'SOLO',
            "laneName": 'TOP',
            "gamesPlayed": 0,
            "matchList": []
        },
        "jungle": {
            "roleName": 'NONE',
            "laneName": 'JUNGLE',
            "gamesPlayed": 0,
            "matchList": []
        },
        "mid": {
            "roleName": 'SOLO',
            "laneName": 'MID',
            "gamesPlayed": 0,
            "matchList": []
        },
        "adc": {
            "roleName": 'DUO_CARRY',
            "laneName": 'BOTTOM',
            "gamesPlayed": 0,
            "matchList": []
        },
        "sup": {
            "roleName": 'DUO_SUPPORT',
            "laneName": 'BOTTOM',
            "gamesPlayed": 0,
            "matchList": []
        }
    }

    for match in matchList['matches']:

        if match['role'] == "SOLO":

            if match['lane'] == "TOP":
                roleDistribution['top']['gamesPlayed'] += 1
                roleDistribution['top']['matchList'].append(match['gameId'])
            else:
                roleDistribution['mid']['gamesPlayed'] += 1
                roleDistribution['mid']['matchList'].append(match['gameId'])

        elif match['role'] == "DUO_CARRY":
            roleDistribution['adc']['gamesPlayed'] += 1
            roleDistribution['adc']['matchList'].append(match['gameId'])
        elif match['role'] == "DUO_SUPPORT":
            roleDistribution['sup']['gamesPlayed'] += 1
            roleDistribution['sup']['matchList'].append(match['gameId'])
        else:
            roleDistribution['jungle']['gamesPlayed'] += 1
            roleDistribution['jungle']['matchList'].append(match['gameId'])

    return roleDistribution

def getRoleStats(matchList, fullmatchList, accountId):

    positionStats = []

    roleDistribution = getRoleDistribution(matchList)

    for position in roleDistribution:
        thisPositionMatchList = roleDistribution[position]['matchList']
        thisPositionMatches = []

        for matchId in thisPositionMatchList:

            for match in fullmatchList:

                if matchId == match[0]['gameId']:
                    thisPositionMatches.append(match[0])
                    break

        thisPositionStats = {
            "wins": 0,
            "losses": 0,
            "gamesPlayed": roleDistribution[position]['gamesPlayed']
        }

        for match in thisPositionMatches:
            player_ids = match['participantIdentities']

            for curr_player in player_ids:
                curr_player_Id = curr_player['participantId']
                curr_player_info = curr_player['player']

                if curr_player_info['accountId'] == accountId:
                    user_participantId = curr_player_Id
                    break

            all_participants = match['participants']

            for participant in all_participants:

                if participant['participantId'] != user_participantId:
                    continue
                else:
                    user_stats = participant['stats']

            if user_stats['win'] == True:
                thisPositionStats['wins'] += 1
            else:
                thisPositionStats['losses'] += 1

        if thisPositionStats['wins'] == 0:
            thisPositionStats['winrate'] = 0
        else:
            thisPositionStats['winrate'] = round((thisPositionStats['wins'] / thisPositionStats['gamesPlayed']) * 100, 1)

        positionStats.append(thisPositionStats)

    return positionStats    

def getMatchlistOnChampion(championId, matchList):

    matchesOnChampion = []

    for match in matchList['matches']:
        thisMatchId = match['gameId']

        if match['champion'] == championId:
            matchesOnChampion.append(thisMatchId)

    return matchesOnChampion

def getMatchesOnChampionsPlayed(championIdList, matchList, fullmatchList):
    championsPlayedMatches = []

    for championId in championIdList:
        championMatchList = getMatchlistOnChampion(championId, matchList)
        championMatches = []

        for matchId in championMatchList:
            
            for match in fullmatchList:
                
                if matchId == match[0]['gameId']:
                    championMatches.append(match[0])
                    break

        championsPlayedMatches.append(championMatches)

    return championsPlayedMatches            

def getStatsOnChampion(matchesOnChampion, accountId):

    matchListTotals = {
        'totalWins': 0,
        'totalKills': 0,
        'totalDeaths': 0,
        'totalAssists': 0
    }

    for match in matchesOnChampion:
        player_ids = match['participantIdentities']

        for curr_player in player_ids:
            curr_player_Id = curr_player['participantId']
            curr_player_info = curr_player['player']

            if curr_player_info['accountId'] == accountId:
                user_participantId = curr_player_Id
                break

        all_participants = match['participants']

        for participant in all_participants:

            if participant['participantId'] != user_participantId:
                continue
            else:
                user_stats = participant['stats']   
        
        if user_stats['win'] == True:
            matchListTotals['totalWins'] += 1

        matchListTotals['totalKills'] += user_stats['kills']
        matchListTotals['totalDeaths'] += user_stats['deaths']
        matchListTotals['totalAssists'] += user_stats['assists']

    StatsOnChampion = {
        'winrate': round((matchListTotals['totalWins'] / len(matchesOnChampion)) * 100, 1),
        'avgKills': round(matchListTotals['totalKills'] / len(matchesOnChampion), 1),
        'avgDeaths': round(matchListTotals['totalDeaths'] / len(matchesOnChampion), 1),
        'avgAssists': round(matchListTotals['totalAssists'] / len(matchesOnChampion), 1),
        'avgKda': round((matchListTotals['totalKills'] + matchListTotals['totalAssists']) / matchListTotals['totalDeaths'], 2)
    }

    return StatsOnChampion

def getTopFiveStats(TopFiveMatches, accountId):

    TopFiveStatsList = []

    for championMatches in TopFiveMatches:

        championStats = getStatsOnChampion(championMatches, accountId)
        TopFiveStatsList.append(championStats)

    return TopFiveStatsList

def sortGamePicks(participantRoles, participants, user_participantId, user_teamColor):

    if user_teamColor == 100:
        user_side = 100
    else:
        user_side = 200     

    userPick = {
        "role": None,
        "champ": None,
        "Id": user_participantId
    }
    userOpponent = {
        "role": None,
        "champ": None,
        "Id": None
    }
    userTeam = {
        "top": None,
        "jungle": None,
        "mid": None,
        "bot": None,
        "supp": None
    }
    enemyTeam = {
        "top": None,
        "jungle": None,
        "mid": None,
        "bot": None,
        "supp": None
    }

    #Setting the user's role and champ
    for Id in participantRoles:
        if Id == user_participantId:
            userPick['role'] = participantRoles[Id]
            for participant in participants:
                if participant['participantId'] == Id:
                    userPick['champ'] = getChampion(participant['championId'])

    #User's lane opponent's role, Id and champ
    for Id in participantRoles:
        if participantRoles[Id] == userPick['role'] and Id != user_participantId:
            userOpponent['role'] = participantRoles[Id]
            userOpponent['Id'] = Id
            for participant in participants:
                if participant['participantId'] == Id:
                    userOpponent['champ'] = getChampion(participant['championId'])

    #Populating user's team and enemy team dicts with champions played, sorted from top to support
    for Id in participantRoles:
        for participant in participants:
            if participant['participantId'] == Id and participant['teamId'] == user_side:
                userTeam[participantRoles[Id]] = getChampion(participant['championId'])
            elif participant['participantId'] == Id and participant['teamId'] != user_side:
                enemyTeam[participantRoles[Id]] = getChampion(participant['championId'])

    #Removing keys from previously used dict to separate user's lane from the rest of the players in the game
    for key, value in userTeam.items():
        if key == userPick['role']:
            userTeam.pop(key)
            break
    for key, value in enemyTeam.items():
        if key == userOpponent['role']:
            enemyTeam.pop(key)
            break

    #Defining the return variable for more organized output
    gamePicks = {
        "userPick":{
            "role": userPick['role'],
            "champ": userPick['champ']
        },
        "userOpponent":{
            "role": userOpponent['role'],
            "champ": userOpponent['champ']
        },
        "userTeam": userTeam,
        "enemyTeam": enemyTeam
    }

    return gamePicks

def sortMatchHistory(matchList, accountId, gameLimit):

    sortedMatchHistory = []

    matchListFiltered = [x for x in matchList if x[0]['gameDuration'] >= 900]

    for matchTuple in matchListFiltered:

        if len(sortedMatchHistory) < gameLimit:
            
            participantRoles = roleml.predict(matchTuple[0], matchTuple[1])

            match = matchTuple[0]

            for participant in match['participantIdentities']:
                thisPlayerData = participant['player']
                thisParticipantId = participant['participantId']

                if thisPlayerData['accountId'] == accountId:
                    user_participantId = thisParticipantId
                    break
                else:
                    continue    

            for participant in match['participants']:
                
                if participant['participantId'] == user_participantId:
                    user_matchStats = participant['stats']
                    userBuildData = participant

                    if participant['teamId'] == 100:
                        user_teamColor = 'blue'
                    else:
                        user_teamColor = 'red'
                    break
                else:
                    continue

            userBuild = getUserBuild(userBuildData)
            teamStats = getTeamStats(match, user_teamColor, user_participantId)

            userSortedStats = {
                "gameId": match['gameId'],
                "timestamp": int(round(match['gameCreation'] / 1000)),
                "gameDuration": convertTime(match['gameDuration']),
                "teamColor": user_teamColor,
                "kills": user_matchStats['kills'],
                "deaths": user_matchStats['deaths'],
                "assists": user_matchStats['assists'],
                "champDmg": user_matchStats['totalDamageDealtToChampions'],
                "visionScore": user_matchStats['visionScore'],
                "controlWards": user_matchStats['visionWardsBoughtInGame'],
                "wardsPlaced": user_matchStats['wardsPlaced'],
                "wardsKilled": user_matchStats['wardsKilled'],
                "goldEarned": user_matchStats['goldEarned'],
                "champLevel": user_matchStats['champLevel'],
                "turretDmg": user_matchStats['damageDealtToTurrets'],
                "objectiveDmg": user_matchStats['damageDealtToObjectives'],
                "takenDmg": user_matchStats['totalDamageTaken'],
                "creepScore": (user_matchStats['totalMinionsKilled'] + user_matchStats['neutralMinionsKilled']),
                "gamePicks": sortGamePicks(participantRoles, match['participants'], user_participantId, user_teamColor),
                "teamStats": teamStats,
                "summonerspells": userBuild['summonerspells'],
                "items": userBuild['items'],
                "runes": userBuild['runes']
            }
            if user_matchStats['win'] == False:
                userSortedStats['outcome'] = 'DEFEAT'
            elif user_matchStats['win'] == True:
                userSortedStats['outcome'] = 'VICTORY'
            else:
                userSortedStats['outcome'] = 'REMAKE'

            if userSortedStats['deaths'] == 0:
                userSortedStats['kda'] = userSortedStats['kills'] + userSortedStats['assists']
            else:
                userSortedStats['kda'] = round((userSortedStats['kills'] + userSortedStats['assists']) / userSortedStats['deaths'], 2)    

            gameTimeSeconds = (userSortedStats['gameDuration']['minutes'] * 60) + userSortedStats['gameDuration']['seconds']
            csPerMin = round((userSortedStats['creepScore'] / gameTimeSeconds) * 60, 1)
            userSortedStats['csPerMin'] = csPerMin

            if userSortedStats['kills'] == 0 and userSortedStats['assists'] == 0:
                userKillParticipation = 0
            else:    
                userKillParticipation = round(((userSortedStats['kills'] + userSortedStats['assists']) / teamStats['totalTeamKills']) * 100, 1)
            userSortedStats['killParticipation'] = userKillParticipation

            sortedMatchHistory.append(userSortedStats)
            continue
        else:
            break    

    return sortedMatchHistory

def getTeamStats(thisMatch, user_teamColor, user_participantId):

    if user_teamColor == 'blue':
        teamId = 100
    elif user_teamColor == 'red':
        teamId = 200    

    for team in thisMatch['teams']:
        
        if team['teamId'] == 100:
            blueTowerKills = team['towerKills']
            blueDragonKills = team['dragonKills']
            blueBaronKills = team['baronKills']
        else:
            redTowerKills = team['towerKills']
            redDragonKills = team['dragonKills']
            redBaronKills = team['baronKills']

    totalTeamKills = 0

    for participant in thisMatch['participants']:
        if participant['teamId'] == teamId:
            thisAllyKills = participant['stats']['kills']
            totalTeamKills += thisAllyKills

    teamStats = {
        "blueTowerKills": blueTowerKills,
        "blueDragonKills": blueDragonKills,
        "blueBaronKills": blueBaronKills,
        "redTowerKills": redTowerKills,
        "redDragonKills": redDragonKills,
        "redBaronKills": redBaronKills,
        "totalTeamKills": totalTeamKills
    }

    return teamStats

def unpackMatchData(matchList):

    matchHistoryData = []
    championsPlayed = {}

    for match in matchList:
        if match['champion'] in championsPlayed.keys():
            championsPlayed[match['champion']] += 1
        else:
            championsPlayed[match['champion']] = 1

        this_matchData_raw = MatchData.query.filter_by(match_id=match['Id']).first()

        while this_matchData_raw:
            this_matchData_decoded = this_matchData_raw.data
            this_matchData = json.loads(this_matchData_decoded)
            this_matchData['timeSince'] = getTimeSince(this_matchData['timestamp'])
            matchHistoryData.append(this_matchData)
            break

    championDict = {k: v for k, v in sorted(championsPlayed.items(), key=lambda item: item[1], reverse=True)}
    championList = list(championDict.keys())

    return (matchHistoryData, championDict, championList)

def unpackTop5(top5Champions, matchHistoryData):

    statsOnTop5 = []

    for champ in top5Champions:
        champMatchList = []

        for match in matchHistoryData:

            if match['gamePicks']['userPick']['champ'] == str(champ):
                champMatchList.append(match)
                continue

        championTotals = {
            'totalWins': 0,
            'totalKills': 0,
            'totalDeaths': 0,
            'totalAssists': 0
        }

        while champMatchList:
            for match in champMatchList:
                if match['outcome'] == 'VICTORY':
                    championTotals['totalWins'] += 1
                championTotals['totalKills'] += match['kills']
                championTotals['totalDeaths'] += match['deaths']
                championTotals['totalAssists'] += match['assists']
            break    
        
        if len(champMatchList) == 0:
            statsOnChampion = {
            'champ': " ",
            'gamesPlayed': " ",
            'winrate': " ",
            'avgKills': " ",
            'avgDeaths': " ",
            'avgAssists': " ",
            'avgKda': " "
        }
        else:
            statsOnChampion = {
                'champ': str(champ),
                'gamesPlayed': len(champMatchList),
                'winrate': round((championTotals['totalWins'] / len(champMatchList)) * 100, 1),
                'avgKills': round(championTotals['totalKills'] / len(champMatchList), 1),
                'avgDeaths': round(championTotals['totalDeaths'] / len(champMatchList), 1),
                'avgAssists': round(championTotals['totalAssists'] / len(champMatchList), 1),
                'avgKda': round((championTotals['totalKills'] + championTotals['totalAssists']) / championTotals['totalDeaths'], 2)
            }
            
        statsOnTop5.append(statsOnChampion)

    if len(statsOnTop5) < 5:
        statsOnChampion = {
            'champ': " ",
            'gamesPlayed': " ",
            'winrate': " ",
            'avgKills': " ",
            'avgDeaths': " ",
            'avgAssists': " ",
            'avgKda': " "
        }
        statsOnTop5.append(statsOnChampion)

    return statsOnTop5

def unpackRoleStats(matchHistoryData):

    roleStats = {
        'top': {
            'gamesPlayed': 0,
            'winrate': 0
        },
        'jungle': {
            'gamesPlayed': 0,
            'winrate': 0
        },
        'mid': {
            'gamesPlayed': 0,
            'winrate': 0
        },
        'bot': {
            'gamesPlayed': 0,
            'winrate': 0
        },
        'supp': {
            'gamesPlayed': 0,
            'winrate': 0
        }
    }

    for role in list(roleStats.keys()):
        
        roleMatchList = []

        for match in matchHistoryData:
            
            if match['gamePicks']['userPick']['role'] == str(role):
                roleMatchList.append(match)
                roleStats[role]['gamesPlayed'] += 1
                continue

        totalWins = 0

        for match in roleMatchList:
            if match['outcome'] == 'VICTORY':
                totalWins += 1
        
        if len(roleMatchList) != 0:
            roleStats[str(role)]['winrate'] = round((totalWins / len(roleMatchList)) * 100, 1)
        else:
            roleStats[str(role)]['winrate'] = 0

    return roleStats

def updateSummonerData(summoner_id, summonerId):

    check_SummonerData = SummonerRank.query.filter_by(summoner_id=summoner_id)

    if check_SummonerData:
        updated_SummonerInfo = loop.run_until_complete(getSummonerInfo(summonerId))
        updated_SummonerInfo = updated_SummonerInfo[0]

        updated_SummonerData = SummonerRank.query.filter_by(summoner_id=summoner_id)\
                                                 .update({SummonerRank.tier: updated_SummonerInfo['tier'],
                                                         SummonerRank.division: updated_SummonerInfo['rank'],
                                                         SummonerRank.wins: updated_SummonerInfo['wins'],
                                                         SummonerRank.losses: updated_SummonerInfo['losses'],
                                                         SummonerRank.leaguePoints: updated_SummonerInfo['leaguePoints']})

    else:
        SummonerInfo = loop.run_until_complete(getSummonerInfo(summonerId))
        SummonerInfo = SummonerInfo[0]

        new_SummonerRank = SummonerRank(tier=SummonerInfo['tier'], division=SummonerInfo['rank'], wins=SummonerInfo['wins'],
                                        losses=SummonerInfo['losses'], leaguePoints=SummonerInfo['leaguePoints'],
                                        summoner_id=check_summoner.id)
        db.session.add(new_SummonerRank)
        db.session.commit()

    return None

def updateSummonerMatches(summoner_id, matchList, expire):

    games_tostore = []

    if expire == True:
        expire_count = 0
        new_matchesList = []

        for match in matchList:
            this_gameId = match['gameId']
            check_match = Match.query.filter_by(gameId=this_gameId, summoner_id=summoner_id).first()
            
            if check_match:
                continue
            else:
                expire_count += 1
                new_matchesList.append(match)

        if expire_count != 0:
            oldest_matches = Match.query.filter_by(summoner_id=summoner_id).order_by(Match.timestamp).limit(expire_count).all()
            # Getting position of the most recent game in the list of the oldest, so it can be used as a cutoff
            cutoff_number = expire_count-1
            # Getting timestamp of the cutoff game
            cutoff_match = oldest_matches[cutoff_number]
            too_old = cutoff_match.timestamp
            # Getting list of match IDs, so the matchdata for it can also be deleted
            expired_match_ids = []
            expired_matches = Match.query.filter_by(summoner_id=summoner_id).filter(Match.timestamp <= too_old).all()
            for match in expired_matches:
                expired_match_ids.append(match.id)
            # Deleting all matches below the cutoff timestamp
            expire_matches = Match.query.filter_by(summoner_id=summoner_id).filter(Match.timestamp <= too_old).delete()
            db.session.commit()
            # Deleting all matchdata for games below the cutoff
            for match_id in expired_match_ids:
                MatchData.query.filter_by(match_id=match_id).delete()
                db.session.commit()
            
        for match in new_matchesList:
            this_gameId = match['gameId']
            
            game_time = round(match['timestamp'] / 1000)
            time_now = time.time()
            date_now = datetime.datetime.fromtimestamp(time_now)
            game_date = datetime.datetime.fromtimestamp(game_time)
            time_between = relativedelta.relativedelta(date_now, game_date)

            if time_between.years == 0 and time_between.months < 3:

                championName = getChampion(match['champion'])

                new_match = Match(gameId=this_gameId, champion=championName, timestamp=match['timestamp'], summoner_id=summoner_id)
                db.session.add(new_match)
                db.session.commit()

                games_tostore_temp = {}
                games_tostore_temp['gameId'] = match['gameId']
                games_tostore.append(games_tostore_temp)

    else:

        for match in matchList:
            this_gameId = match['gameId']
            check_match = Match.query.filter_by(gameId=this_gameId, summoner_id=summoner_id).first()

            if check_match:
                continue
            else:

                game_time = round(match['timestamp'] / 1000)
                time_now = time.time()
                date_now = datetime.datetime.fromtimestamp(time_now)
                game_date = datetime.datetime.fromtimestamp(game_time)
                time_between = relativedelta.relativedelta(date_now, game_date)

                if time_between.years == 0 and time_between.months < 3:

                    championName = getChampion(match['champion'])

                    new_match = Match(gameId=this_gameId, champion=championName, timestamp=match['timestamp'], summoner_id=summoner_id)
                    db.session.add(new_match)
                    db.session.commit()

                    games_tostore_temp = {}
                    games_tostore_temp['gameId'] = match['gameId']
                    games_tostore.append(games_tostore_temp)

    return games_tostore

def updateSummonerMatchData(matches, timelines, accountId, summoner_id):

    if matches and timelines:
        fullmatchList = merge(matches, timelines)

        matchData_tostore = sortMatchHistory(fullmatchList, accountId, len(matches))

        for match in matchData_tostore:
            thisMatch_data = json.dumps(match, indent=24)

            match_id_game = Match.query.filter_by(gameId=match['gameId'], summoner_id=summoner_id).first()

            while match_id_game:
                match_id = match_id_game.id

                new_MatchData = MatchData(gameId=match['gameId'], data=thisMatch_data, summoner_id=summoner_id,
                                        match_id=match_id)
                db.session.add(new_MatchData)
                db.session.commit()
                break

    return None

def expireOldMatches(summoner_id):

    too_old = datetime.datetime.utcnow() - datetime.timedelta(days=60)
    expire_matches = Match.query.filter_by(summoner_id=summoner_id).filter(Match.date_saved <= too_old).delete()
    db.session.commit()
    expire_matchdata = MatchData.query.filter_by(summoner_id=summoner_id).filter(MatchData.date_saved <= too_old).delete()
    db.session.commit()

    return (expire_matches, expire_matchdata)

def registerSummoner(summonerId, accountId, name, profileIconId, summonerLevel):

    new_Summoner = Summoner(summonerId=summonerId, accountId=accountId, name=name,
                            profileIconId=profileIconId, summonerLevel=summonerLevel)
    db.session.add(new_Summoner)
    db.session.commit()
    new_Summoner = Summoner.query.filter_by(accountId=accountId).first()
    summoner_info = loop.run_until_complete(getSummonerInfo(summonerId))
    print(summoner_info)
    time.sleep(3)
    summoner_info = summoner_info[0]
    new_SummonerRank = SummonerRank(tier=summoner_info['tier'], division=summoner_info['rank'], wins=summoner_info['wins'],
                                    losses=summoner_info['losses'], leaguePoints=summoner_info['leaguePoints'],
                                    summoner_id=new_Summoner.id)
    db.session.add(new_SummonerRank)
    db.session.commit()

    return new_Summoner

def registerSummonerMatches(accountId, summoner_id):

    gameAmount = 40
    matchList = loop.run_until_complete(getRecentMatchlist(accountId, 0, gameAmount))
    matchList = matchList['matches']

    sortedMatchList = []

    for match in matchList:

        game_time = round(match['timestamp'] / 1000)
        time_now = time.time()
        time_now = datetime.datetime.fromtimestamp(time_now)
        game_date = datetime.datetime.fromtimestamp(game_time)
        time_between = relativedelta.relativedelta(time_now, game_date)

        if time_between.years == 0 and time_between.months < 3: 

            championName = getChampion(match['champion'])

            new_Match = Match(gameId=match['gameId'], champion=championName, timestamp=match['timestamp'],
                          summoner_id=summoner_id)
            db.session.add(new_Match)
            db.session.commit()

            games_tostore_temp = {}
            games_tostore_temp['gameId'] = match['gameId']
            sortedMatchList.append(games_tostore_temp)
        else:
            continue

    return sortedMatchList
        
def registerSummonerMatchData(matches, timelines, accountId, summoner_id):

    fullmatchList = merge(matches, timelines)
    
    matchData_tostore = sortMatchHistory(fullmatchList, accountId, len(matches))

    for match in matchData_tostore:
        thisMatch_data = json.dumps(match, indent=24)

        match_id_game = Match.query.filter_by(gameId=match['gameId'], summoner_id=summoner_id).first()

        while match_id_game:
            match_id = match_id_game.id

            new_MatchData = MatchData(gameId=match['gameId'], data=thisMatch_data, summoner_id=summoner_id,
                                    match_id=match_id)
            db.session.add(new_MatchData)
            db.session.commit()
            break

    return None

def getSingleGameTags(matchHistoryData):

    rev_matchHistoryData = [ele for ele in reversed(matchHistoryData)]
    tags = []

    matchCount = 0
    losses = 0
    wins = 0
    lossStreak = 0
    winStreak = 0

    for match in rev_matchHistoryData:
        thisGameTags = {
            'goodTags': [],
            'badTags': [],
            'godTag': []
        }

        # Give 'Break Time' tag if the user has lost three or more games in a row
        if match['outcome'] == 'DEFEAT':
            lossStreak += 1
            if lossStreak >= 3:
                thisGameTags['badTags'].append('Break Time')
            winStreak = 0
            losses += 1
            matchCount += 1
        # Give 'Win Streak' tag if the user has won three or more games in a row
        elif match['outcome'] == 'VICTORY':
            lossStreak = 0
            winStreak += 1
            wins += 1
            matchCount += 1
            if winStreak >= 3:
                thisGameTags['goodTags'].append('Win Streak')
        
        last_6 = rev_matchHistoryData[matchCount-6:matchCount]
        if last_6:
            last_6_wins = 0
            for match in last_6:
                if match['outcome'] == 'VICTORY':
                    last_6_wins += 1

            if last_6_wins >= 4 and match['outcome'] == 'VICTORY':
                thisGameTags['goodTags'].append('On Fire')        

        userRole = match['gamePicks']['userPick']['role'].lower()

        # Giving tags based on a summoner's farming efficiency, relative to what is expected of their role
        if match['csPerMin'] <= 6:
            if userRole != 'supp':
                if match['outcome'] == 'DEFEAT':
                    thisGameTags['badTags'].append('Starving')
                if match['outcome'] == 'VICTORY':
                    thisGameTags['badTags'].append('Inefficient')
        elif match['csPerMin'] >= 6:
            thisGameTags['goodTags'].append('Good Farming')

        # Giving good tags based on a summoner's kill-share, relative to what is expected of their role
        if userRole == 'top':
            if match['killParticipation'] <= 38.9:
                thisGameTags['badTags'].append('Viewer')
            
            elif match['killParticipation'] >= 58:
                if match['outcome'] == 'VICTORY':
                    thisGameTags['goodTags'].append('Ever-present')
                elif match['outcome'] == 'DEFEAT':
                    thisGameTags['goodTags'].append('Fighter')

                    if match['kda'] >= 5 and match['csPerMin'] >= 6:
                        thisGameTags['goodTags'].append('Unlucky')

        elif userRole == 'jungle':
            if match['killParticipation'] <= 41.9:
                thisGameTags['badTags'].append('Viewer')
            
            elif match['killParticipation'] >= 62:
                if match['outcome'] == 'VICTORY':
                    thisGameTags['goodTags'].append('Ever-present')
                elif match['outcome'] == 'DEFEAT':
                    thisGameTags['goodTags'].append('Fighter')

                    if match['kda'] >= 5 and match['csPerMin'] >= 6:
                        thisGameTags['goodTags'].append('Unlucky')

        elif userRole == 'mid':
            if match['killParticipation'] <= 41.9:
                thisGameTags['badTags'].append('Viewer')
            
            elif match['killParticipation'] >= 62:
                if match['outcome'] == 'VICTORY':
                    thisGameTags['goodTags'].append('Ever-present')
                elif match['outcome'] == 'DEFEAT':
                    thisGameTags['goodTags'].append('Fighter')

                    if match['kda'] >= 5 and match['csPerMin'] >= 6:
                        thisGameTags['goodTags'].append('Unlucky')

        elif userRole == 'bot':
            if match['killParticipation'] <= 41.9:
                thisGameTags['badTags'].append('Viewer')

            elif match['killParticipation'] >= 60:
                if match['outcome'] == 'VICTORY':
                    thisGameTags['goodTags'].append('Ever-present')
                elif match['outcome'] == 'DEFEAT':
                    thisGameTags['goodTags'].append('Fighter')

                    if match['kda'] >= 5 and match['csPerMin'] >= 6:
                        thisGameTags['goodTags'].append('Unlucky')

        elif userRole == 'supp':
            if match['killParticipation'] <= 46.9:
                thisGameTags['badTags'].append('Viewer')

            elif match['killParticipation'] >= 64:
                if match['outcome'] == 'VICTORY':
                    thisGameTags['goodTags'].append('Ever-present')
                elif match['outcome'] == 'DEFEAT':
                    thisGameTags['goodTags'].append('Fighter')

                    if match['kda'] >= 5:
                        thisGameTags['goodTags'].append('Unlucky')

        # Giving tags if the summoner performed more than admirably
        if match['kda'] >= 8:
            thisGameTags['goodTags'].append('Untouchable')
        
        if match['kda'] >= 4:
            if match['outcome'] == 'VICTORY' and match['killParticipation'] >= 60:
                if userRole == 'supp':
                    thisGameTags['godTag'].append('Virtuoso')
                else:
                    if match['csPerMin'] >= 6:
                        thisGameTags['godTag'].append('Virtuoso')

        elif match['kda'] >= 2.5 and match['kda'] < 4:
            thisGameTags['goodTags'].append('Good KDA')

        elif match['kda'] <= 1.5 and match['deaths'] >= match['kills'] * 1.5 and match['deaths'] >= 6:
            thisGameTags['badTags'].append('Zombie')

        if 'wardsPlaced' in match.keys():
            if userRole == 'supp':
                if match['wardsPlaced'] / 5 >= 3.5:
                    thisGameTags['goodTags'].append('Sightstone')
                elif match['wardsPlaced'] / 5 <= 2:
                    thisGameTags['badTags'].append('Dark Map')

                if match['controlWards'] / 5 >= 1.2 and match['wardsKilled'] / 5 >= 1:
                    thisGameTags['goodTags'].append('All-Seeing')
                elif match['controlWards'] / 5 <= 1 or match['wardsKilled'] / 5 < 0.8:
                    thisGameTags['badTags'].append('Bad Control')
            else:
                if match['wardsPlaced'] / 5 >= 1.2:
                    thisGameTags['goodTags'].append('Sightstone')
                elif match['wardsPlaced'] / 5 <= 1:
                    thisGameTags['badTags'].append('Dark Map')

                if match['controlWards'] / 5 >= 0.8 and match['wardsKilled'] / 5 >= 0.6:
                    thisGameTags['goodTags'].append('All-Seeing')
                elif match['controlWards'] / 5 <= 0.5 or match['wardsKilled'] / 5 < 0.4:
                    thisGameTags['badTags'].append('Bad Control')

        tags.append(thisGameTags)

    return reversed(tags)