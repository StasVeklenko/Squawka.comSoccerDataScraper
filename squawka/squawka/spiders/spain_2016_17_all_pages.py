from scrapy_splash import SplashRequest
from scrapy import Spider
from scrapy.projects.squawka.squawka.excel import spreadsheet
from bs4 import BeautifulSoup
from collections import OrderedDict
import codecs, win_unicode_console

class MySpider(Spider):
    name = 'spain_2016_17_all_pages'
    url = 'http://www.squawka.com/match-results'
    page = 10 #total number of pages on the link/last page we want to scrape from
    matchLinks = list()
    fieldsRow = 1 #row of column names (fields) of table
    firstFieldsColumn = 1 #column of a first column (field) of table
    fieldsAmount = 14 #number of columns (fields)
    lastFieldsColumn = firstFieldsColumn + fieldsAmount - 1
    inputRow = 2 #first input row (we put the list of fields into the first row of the spreadsheet first)
    
    #scheme: do a request to initial url -> execute Lua script 'select La Liga, 2016/17 from the dropdown menus; collect all the links to pages with actual match data (for all pages)' -> after collection, go to each (one by one) 
    #start_requests() sets up the spanish parameters, parser just goes to links
    def start_requests(self):
        def returnMatchListScript(pageNumber):
            
            matchListScript = """
            function main(splash, args)
              splash.private_mode_enabled = False
              
              assert(splash:go(args.url))
              
              assert(splash:wait(5))
              
              splash:evaljs("document.querySelector('div#sq-pagination span.current').nextElementSibling.click()")
              assert(splash:wait(3))
              
              splash:evaljs("document.querySelector(\\"select[id='league-filter-list'] option[value='23']\\").selected = true")
              
              assert(splash:wait(2))
              
              splash:evaljs("document.querySelector(\\"select[id='league-filter-list']\\").onchange()")
              
              assert(splash:wait(2))
              
              splash:evaljs("document.querySelector(\\"select[id='league-season-list'] option[value='2016']\\").selected = true")
              
              assert(splash:wait(2))
              
              splash:evaljs("document.querySelector(\\"select[id='league-season-list']\\").onchange()")
              
              assert(splash:wait(2))
              
              assert(splash:go("http://www.squawka.com/match-results?pg="""+pageNumber+""""))
              
              assert(splash:wait(3))
              
              return splash:html()
            end
            """  
            
            return matchListScript
       
        matchListScripts = []
        win_unicode_console.enable()
        for pageNumber in range(self.page):
            matchListScripts.append(returnMatchListScript(str(pageNumber+1)))
        
        for matchListScript in matchListScripts:
            yield SplashRequest(self.url, self.parseMatchList,
                args={
                    'lua_source': matchListScript
                    # optional; parameters passed to Splash HTTP API
                    # 'wait': 2,
                    # 'url' is prefilled from request url
                    # 'http_method' is set to 'POST' for POST requests
                    # 'body' is set to request body for POST requests
                },
                endpoint = '/execute'
                #slot_policy=scrapy_splash.SlotPolicy.PER_DOMAIN,  # optional
            )            
        
    def parseMatchList(self, response):
        #this function gets all the match links from response and puts them into match_links; then yields separate requests for each 
        self.matchLinks += response.xpath("//table[@class='fixture-results-table']/tbody/tr[@class='match-today']/td[@class='match-centre']/a/@href").extract()
        
        matchScript = """
        function main(splash, args)
          splash.private_mode_enabled = False
          
          assert(splash:go(args.url))
          
          assert(splash:wait(5))
          
          local roomID = splash:evaljs("chatClient.roomID")
          
          assert(splash:wait(2))
          
          assert(splash:go("http://s3-irl-laliga.squawka.com/dp/ingame/"..roomID))
          
          assert(splash:wait(4)) 
        
          return splash:html()
        end
        """           
        
        currentPageNumber = response.xpath("//div[@id='sq-pagination'][1]//span[contains(@class, 'current')]/text()").extract()[0]
        startExcelInput = False
        if int(currentPageNumber) == self.page:
            startExcelInput = True
        
        if startExcelInput: #start following match links in self.match_links and downloading data from them one by one
            for matchLink in self.matchLinks:
                #self.logger.info("The link is: %s", match_link)
                yield SplashRequest(matchLink, self.parseMatch,
                    args={
                        'lua_source': matchScript
                        # optional; parameters passed to Splash HTTP API
                        # 'wait': 2,
                        # 'url' is prefilled from request url
                        # 'http_method' is set to 'POST' for POST requests
                        # 'body' is set to request body for POST requests
                    },
                    endpoint = '/execute'
                    #slot_policy=scrapy_splash.SlotPolicy.PER_DOMAIN,  # optional
                ) 
        
    def parseMatch(self, response):
        playerIds, teamIds, processedXml = {}, {}, BeautifulSoup(str(response.body)[2:-1], "xml")
        
        #player ids
        for each in processedXml.select("players player"):
            playerIds[each.get("id")] = [codecs.escape_decode(each.find("name").get_text().encode("latin-1"))[0].decode("utf-8"), each.get("team_id")]
            
        #team ids
        for each in processedXml.select("data_panel game team"):
            if each.find("state").get_text() == "home":
                homeTeam = codecs.escape_decode(each.find("short_name").get_text().encode("latin-1"))[0].decode("utf-8")
            elif each.find("state").get_text() == "away": 
                awayTeam = codecs.escape_decode(each.find("short_name").get_text().encode("latin-1"))[0].decode("utf-8")
            teamIds[each.get("id")] = [codecs.escape_decode(each.find("short_name").get_text().encode("latin-1"))[0].decode("utf-8"), each.find("state").get_text()]
        
        #setting up the main data container
        data = {
            'date': processedXml.find("squawka").get("date"), #match date
            'home': homeTeam, #home team name
            'away': awayTeam, #away team name
            'goals': {}, #type, player, is_own, mins
            'shots': {}, #type, player, mins
            'shots_on_target': {}, #type, player, mins
            'headed_duals': {}, #player (player_id), otherplayer, success/fail/foul, mins
            'interceptions': {}, #player, mins
            'clearances': {},  #type, player, mins
            'tackles': {}, #player (tackler), opponent (tacklee), success/fail/foul, mins
            'takeons': {}, #player (takeon-ee), other_player (takeon-er), success/fail, mins
            'blocked_events': {}, #player, blocked shot/pass/cross, mins
            'fouls': {}, #player (fouler), opponent (foulee), mins
            'cards': {} #player, card yellow/red, mins
        }      
        
        for key in data.keys():
            if key not in ['date', 'home', 'away']:
                data[key]["home_short"] = 0
                data[key]["away_short"] = 0
                data[key]["home_detailed"] = [] #list of dictionaries, sorted by mins (ascending) (will be sorted naturally, since events will be added in an ascending way)
                data[key]["away_detailed"] = [] #list of dictionaries, sorted by mins (ascending) (will be sorted naturally, since events will be added in an ascending way)      
        
        for key in data.keys():       
            if key in ['goals', 'shots', 'shots_on_target']:
                paramName = 'goals_attempts'
            else:
                paramName = key
                
            if key not in ['date', 'home', 'away']:
                for event in processedXml.select(paramName+' event'):
                    try: #appending data from xml to data
                        if key == "shots":
                            data[key][teamIds[event.get("team_id")][1]+"_detailed"].append({'mins': int(event.get("mins"))+1,
                                'player': playerIds[event.get('player_id')][0], 'type': event.get('type'), "is_own": event.has_attr("is_own") })
                            if not event.has_attr("is_own"):
                                data[key][teamIds[event.get("team_id")][1]+"_short"] += 1
                        if key == "shots_on_target" and event.get("type") in ["save", "wood_work", "goal"]:
                            data[key][teamIds[event.get("team_id")][1]+"_detailed"].append({'mins': int(event.get("mins"))+1,
                                'player': playerIds[event.get('player_id')][0], 'type': event.get('type'), "is_own": event.has_attr("is_own") })
                            if not event.has_attr("is_own"):
                                data[key][teamIds[event.get("team_id")][1]+"_short"] += 1
                        elif key == 'goals' and event.get("type") == "goal":
                            data[key][teamIds[event.get("team_id")][1]+"_detailed"].append({'mins': int(event.get("mins"))+1,
                                'player': playerIds[event.get('player_id')][0], 'type': event.get('type'), "is_own": event.has_attr("is_own") })
                            data[key][teamIds[event.get("team_id")][1]+"_short"] += 1
                        elif key == "headed_duals":
                            data[key][teamIds[event.get("team_id")][1]+"_detailed"].append({'mins': int(event.get("mins"))+1,
                                'player': playerIds[event.get('player_id')][0], 'opponent': playerIds[event.find("otherplayer").get_text()][0],
                                'type': event.get("action_type") })
                            data[key][teamIds[event.get("team_id")][1]+"_short"] += 1
                        elif key == "interceptions":
                            data[key][teamIds[event.get("team_id")][1]+"_detailed"].append({'mins': int(event.get("mins"))+1,
                                'player': playerIds[event.get('player_id')][0], 'headed': bool(event.find("headed")) })
                            data[key][teamIds[event.get("team_id")][1]+"_short"] += 1
                        elif key == "clearances":
                            data[key][teamIds[event.get("team_id")][1]+"_detailed"].append({'mins': int(event.get("mins"))+1,
                                'player': playerIds[event.get('player_id')][0], 'headed': bool(event.find("headed").get_text()) })
                            data[key][teamIds[event.get("team_id")][1]+"_short"] += 1
                        elif key == "tackles":
                            data[key][teamIds[event.find("tackler_team").get_text()][1]+"_detailed"].append({'mins': int(event.get("mins"))+1,
                                'player': playerIds[event.find("tackler").get_text()][0], "type": event.get("type"),
                                'opponent': playerIds[event.get('player_id')][0] })
                            data[key][teamIds[event.find("tackler_team").get_text()][1]+"_short"] += 1
                        elif key == "takeons":
                            data[key][teamIds[event.get("other_team")][1]+"_detailed"].append({'mins': int(event.get("mins"))+1,
                                'player': playerIds[event.get('other_player')][0], 'opponent': playerIds[event.get('player_id')][0],
                                'type': event.get('type') })
                            data[key][teamIds[event.get("other_team")][1]+"_short"] += 1
                        elif key == "blocked_events":
                            data[key][teamIds[event.get("team_id")][1]+"_detailed"].append({'mins': int(event.get("mins"))+1,
                                'player': playerIds[event.get('player_id')][0], 'type': event.get('type') })
                            if event.find("shot") != None:
                                data[key][teamIds[event.get("team_id")][1]+"_detailed"][-1]['shot'] = bool(event.find("shot").get_text())
                            if event.find("headed") != None:
                                data[key][teamIds[event.get("team_id")][1]+"_detailed"][-1]['headed'] = bool(event.find("headed").get_text())
                            if event.get("type") == "blocked_shot" and event.has_attr("shot_player"):
                                data[key][teamIds[event.get("team_id")][1]+"_detailed"][-1]['shot_player'] = playerIds[event.get("shot_player")][0]
                            data[key][teamIds[event.get("team_id")][1]+"_short"] += 1
                        elif key == "fouls":
                            if event.find("otherplayer").get_text() == '0':
                                opponent = "-"
                            else:
                                opponent = playerIds[event.find("otherplayer").get_text()][0]
                            data[key][teamIds[event.get("team")][1]+"_detailed"].append({'mins': int(event.get('mins'))+1,
                                'player': playerIds[event.get('player_id')][0], 'opponent': opponent })
                            data[key][teamIds[event.get("team")][1]+"_short"] += 1
                        elif key == "cards":
                            data[key][teamIds[event.get("team")][1]+"_detailed"].append({'mins': int(event.get('mins'))+1,
                                'player': playerIds[event.get('player_id')][0], 'card': event.find("card").get_text() })
                            data[key][teamIds[event.get("team")][1]+"_short"] += 1
                    except KeyError:
                        print("KEY ERROR: "+key+"; event mins: "+event.get("mins"))
                        print("Match date: "+processedXml.find("squawka").get("date"))
                        print("Teams: "+str(teamIds))
        
        #putting data into excel spreadsheet                      
        squawkaDatasheet = spreadsheet("C:/Users/HP10/AppData/Local/Programs/Python/Python35/Lib/site-packages/scrapy/projects/squawka/squawka/excel/squawka_Spain_2016_17.xlsx","Spain")    #squawka_data_+str(self.page)+".xlsx", "Spain")
        
        #a list of column names
        fieldNames = squawkaDatasheet.getData("Spain", self.fieldsRow, self.firstFieldsColumn, 1, self.fieldsAmount, "row")

        def saveDataToSpreadsheet():
            for eventName in data.keys():
                print("NEW EVENT NAME: "+eventName)
                if eventName in ["interceptions", "clearances"]:
                    detailedLoop(eventName) #"home_detailed"/"away_detailed"/"home_total"/"away_total"

        def detailedLoop(eventName):
            for detailed in data[eventName].keys():  # "home_detailed"/"away_detailed"/"home_total"/"away_total"
                if detailed in ["home_detailed", "away_detailed"]:
                    inputLoop(eventName, detailed)

        def inputLoop(eventName, detailed):
            for event in data[eventName][detailed]:  # {'mins':'25', 'type': 'Possession', ...}
                columnIncrement = 0
                for fieldName in fieldNames:
                    if fieldName in event.keys():
                        squawkaDatasheet.set_data(str(event[fieldName]), "Spain", self.inputRow,
                                                   self.firstFieldsColumn + columnIncrement)  # inputting 1 value at a time
                        # print(field_name+": "+str(event[field_name]))
                    elif fieldName == "total":
                        squawkaDatasheet.set_data(data[eventName][detailed[:4] + "_short"], "Spain", self.inputRow,
                                                   self.firstFieldsColumn + columnIncrement)
                        # print(field_name+": "+str(data[event_name][detailed[:4]+"_short"]))
                    elif fieldName == "event":
                        squawkaDatasheet.set_data(eventName, "Spain", self.inputRow,
                                                   self.firstFieldsColumn + columnIncrement)
                        # print(field_name+": "+str(event_name))
                    elif fieldName == "team":
                        squawkaDatasheet.set_data(data[detailed[:4]], "Spain", self.inputRow,
                                                   self.firstFieldsColumn + columnIncrement)
                        # print(field_name+": "+str(data[detailed[:4]]))
                    elif fieldName in ["home", "away", "date"]:
                        squawkaDatasheet.set_data(data[fieldName], "Spain", self.inputRow,
                                                   self.firstFieldsColumn + columnIncrement)
                        # print(field_name+": "+str(data[field_name]))
                    else:
                        squawkaDatasheet.set_data("-", "Spain", self.inputRow,
                                                   self.firstFieldsColumn + columnIncrement)
                        # print(field_name+": -")
                    columnIncrement += 1
                self.inputRow += 1
                print("=========NEXT EVENT==========")

        saveDataToSpreadsheet()
        print("===============")
        squawkaDatasheet.save()
