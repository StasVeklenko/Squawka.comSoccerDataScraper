#showing total number of goals by interval in the whole season
SELECT intvs.interval, COUNT(*) as total_goals FROM 
  (SELECT CASE  
    WHEN mins between 0 and 15 then '0-15'
    WHEN mins between 15 and 30 then '15-30'
    WHEN mins between 30 and 45 then '30-45'
    WHEN mins between 45 and 60 then '45-60'
    WHEN mins between 60 and 75 then '60-75'
    WHEN mins between 75 and 90 then '75-90'
    WHEN mins > 90 then '90+'
  END AS `interval` 
FROM soccer.shots WHERE type = "goal") AS intvs
GROUP BY intvs.interval
ORDER BY intvs.interval;

#showing number of goals and percentage of goals by interval for teams Athletic, Barcelona, Betis, Celta, Eibar without counting own goals into opponent's net 
SELECT team, COUNT(*) AS `total goals`, ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY team),2) AS `percentage of team goals in interval`, 
CASE 
    WHEN mins BETWEEN 0 AND 15 THEN '0-15'
    WHEN mins BETWEEN 15 AND 30 THEN '15-30'
    WHEN mins BETWEEN 30 AND 45 THEN '30-45'
    WHEN mins BETWEEN 45 AND 60 THEN '45-60'
    WHEN mins BETWEEN 60 AND 75 THEN '60-75'
    WHEN mins BETWEEN 75 AND 90 THEN '75-90'
    WHEN mins > 90 THEN '90+'
END AS `interval`
FROM soccer.shots LEFT JOIN soccer.players ON shots.player = players.player
WHERE `event` = "goals" AND team IN ('Athletic', 'Barcelona', 'Betis', 'Celta', 'Eibar') AND is_own = 0
GROUP BY team, `interval`
ORDER BY team, `interval`;

#show the top 5 players with most fouls
SELECT fouls.player, players2.teams, COUNT(*) AS `total fouls` FROM soccer.fouls LEFT JOIN 
(SELECT player, GROUP_CONCAT(team SEPARATOR '/') AS teams FROM soccer.players GROUP BY player) AS players2
ON fouls.player = players2.player WHERE fouls.player IS NOT NULL GROUP BY fouls.player ORDER BY `total fouls` DESC LIMIT 5;  

#show the top 5 most fouled on players
SELECT fouls.opponent, players2.teams, COUNT(*) AS `total fouled on` FROM soccer.fouls LEFT JOIN 
(SELECT player, GROUP_CONCAT(team SEPARATOR '/') AS teams FROM soccer.players GROUP BY player) AS players2
ON fouls.opponent = players2.player WHERE fouls.opponent IS NOT NULL GROUP BY fouls.opponent ORDER BY `total fouled on` DESC LIMIT 5;

#showing number of goals and percentage of goals by interval for teams Athletic, Barcelona, Betis, Celta, Eibar with counting own goals into opponent's net
SELECT COUNT(*) `total goals`, IF(shots.is_own = 1, IF(players.team = matches.home, matches.away, matches.home), players.team) `scoring team`, 
CASE 
    WHEN mins BETWEEN 0 AND 15 THEN '0-15'
    WHEN mins BETWEEN 15 AND 30 THEN '15-30'
    WHEN mins BETWEEN 30 AND 45 THEN '30-45'
    WHEN mins BETWEEN 45 AND 60 THEN '45-60'
    WHEN mins BETWEEN 60 AND 75 THEN '60-75'
    WHEN mins BETWEEN 75 AND 90 THEN '75-90'
    WHEN mins > 90 THEN '90+'
END `interval`, ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY IF(is_own = 1, IF(players.team = matches.home, matches.away, matches.home), players.team)),2) `share of total goals`  
FROM soccer.shots 
LEFT JOIN soccer.players ON shots.player = players.player
LEFT JOIN soccer.matches ON shots.`date` = matches.`date` AND (players.team = matches.home OR players.team = matches.away)
WHERE `event` = 'goals'
GROUP BY `scoring team`, `interval`
HAVING `scoring team` IN ('Athletic', 'Barcelona', 'Betis', 'Celta', 'Eibar')
ORDER BY `scoring team`, `interval`;

#calculating every Barcelona's player shooting coefficient before each match where this player made a shot/shot on target/goal by this formula:
	#(0.5 * ( total shots on target by player over his last 6 matches ) / (total shots by player over his last 6 matches) + 0.5 * (total goals by player over his last 6 matches ) / ( total shots on target by player over his last 6 matches )) * 
		#  * (0.6 * (total saves by the opponent team over the last 6 matches ) / (total shots on target against the opponent team over the last 6 matches) + 0.4*(total blocked shots by the opponent team after the last 6 matches)/(total shots against the opponent team over the last 6 matches))  
SELECT `proxy`.`date`, `proxy`.home, `proxy`.away, `proxy`.player, `proxy`.team, 
       ROUND(`proxy`.attacking_coef * (0.6*COUNT(CASE WHEN shots2.`event` = 'shots_on_target' AND shots2.`type`='save' THEN 1 ELSE NULL END) / COUNT(CASE WHEN shots2.`event` = 'shots_on_target' THEN 1 ELSE NULL END) + 0.4*COUNT(CASE WHEN shots2.`event` = 'shots' AND shots2.`type` = 'blocked' THEN 1 ELSE NULL END)/COUNT(CASE WHEN shots2.`event` = 'shots' THEN 1 ELSE NULL END)),3) AS `shooting coefficient`
     FROM 
    (SELECT shots.`date`, shots.player, players.team, shots.`event`, shots.`type` FROM soccer.shots
    LEFT JOIN soccer.players ON shots.player = players.player WHERE is_own = 0 ORDER BY shots.`date`) AS shots2
    LEFT JOIN
    (SELECT table1.`date` AS `date`, table1.home AS home, table1.away AS away, player, team, attacking_coef, matches.`date` AS opp_date, matches.home AS opp_home, matches.away AS opp_away, ROW_NUMBER() OVER (PARTITION BY table1.player, table1.home, table1.away ORDER BY matches.`date` DESC) AS row_num FROM
        (SELECT `date`, home, away, player, team, attacking_coef FROM (
            SELECT *,  IF(unique_match = 1, NULL,
							IFNULL(ROUND(
										0.5*(COUNT(CASE WHEN `event`='shots_on_target' THEN 1 ELSE NULL END) OVER (PARTITION BY player ORDER BY CAST(unique_match AS SIGNED) RANGE BETWEEN 6 PRECEDING AND 1 PRECEDING)) / (COUNT(CASE WHEN `event` IN ('shots_on_target', 'shots') THEN 1 ELSE NULL END) OVER (PARTITION BY player ORDER BY CAST(unique_match AS SIGNED) RANGE BETWEEN 6 PRECEDING AND 1 PRECEDING)) +
                                        0.5*(COUNT(CASE WHEN `event`='goals' THEN 1 ELSE NULL END) OVER (PARTITION BY player ORDER BY CAST(unique_match AS SIGNED) RANGE BETWEEN 6 PRECEDING AND 1 PRECEDING)) / (COUNT(CASE WHEN `event` IN ('goals', 'shots_on_target') THEN 1 ELSE NULL END) OVER (PARTITION BY player ORDER BY CAST(unique_match AS SIGNED) RANGE BETWEEN 6 PRECEDING AND 1 PRECEDING))
                                        , 3), 0)) AS attacking_coef FROM 
                (SELECT shots.`date`, home, away, shots.player, team, `event`, 
                DENSE_RANK() OVER (PARTITION BY shots.player ORDER BY shots.`date`, matches.home, matches.away) AS unique_match 
                FROM soccer.shots
                LEFT JOIN soccer.players ON shots.player = players.player
                LEFT JOIN soccer.matches ON players.team = IF(players.team = matches.home, matches.home, matches.away) AND shots.`date` = matches.`date`
                WHERE (team = 'Barcelona' AND `event` IN ('shots_on_target', 'shots', 'goals') AND is_own=0)) AS ini 
             ) AS ini2
             WHERE `event` = 'shots' GROUP BY player, unique_match) AS table1 
    LEFT JOIN soccer.matches ON table1.`date` > matches.`date` 
    WHERE IF(table1.team = table1.home,table1.away,table1.home) IN (matches.home, matches.away) 
    ORDER BY player, `date`, row_num DESC) AS `proxy`    
ON `proxy`.opp_date = shots2.`date` AND (`proxy`.opp_home = shots2.team OR `proxy`.opp_away = shots2.team)
WHERE `proxy`.row_num <= 6 AND shots2.team = IF(`proxy`.opp_home = IF(`proxy`.team = `proxy`.home, `proxy`.away, `proxy`.home), `proxy`.opp_away, `proxy`.opp_home)
GROUP BY `proxy`.player, `proxy`.home, `proxy`.away 
ORDER BY `proxy`.player, `proxy`.`date`, `proxy`.row_num DESC;

 


