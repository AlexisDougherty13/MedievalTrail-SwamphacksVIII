import discord
import os
import server
import discord.ext.commands
import random
from pymongo import MongoClient
from replit import db
import json
import string
import time
from datetime import date

#num, name, miles until dest
checkpoints = [
  (0, "Kingdom of Welic", 248),
  (1, "", 240),
  (2, "", 232),
  (3, "", 224),
  (4, "", 216),
  (5, "Rushing River", 176), #longer route is 208 for this spot
  (6, "", 168),
  (7, "", 160),
  (8, "", 152),
  (9, "", 144),
  (10, "Harwelver", 136),
  (11, "", 200),
  (12, "", 192),
  (13, "", 184),
  (14, "", 176),
  (15, "Cliffs of Insanity", 168),
  (16, "", 160),
  (17, "", 152),
  (18, "", 144),
  (19, "", 136),
  (20, "", 128),
  (21, "Dailion Keep", 120), #landmark
  (22, "", 128),
  (23, "", 120),
  (24, "", 112),
  (25, "Dragon Fortress", 104),
  (26, "", 96),
  (27, "", 88),
  (28, "", 80),
  (29, "", 72),
  (30, "", 64),
  (31, "", 56),
  (32, "Forbidden Forest", 48), #landmark
  (33, "", 112),
  (34, "", 104),
  (35, "", 96),
  (36, "", 88),
  (37, "", 80),
  (38, "", 72),
  (39, "", 64),
  (40, "", 56),
  (41, "", 40),
  (42, "", 32),
  (43, "", 24),
  (44, "", 16),
  (45, "", 8),
  (46, "Kingdom of Ni", 0),
]

mongoClient = MongoClient(str(os.getenv("MONGO_KEY")))
db = mongoClient.MedievalTrail
gamesTable = db.Games

client = discord.Client()

def inGame(id):
  for x in gamesTable.find():
    for y in x["Players"]:
      if y == id:
        return True
  return False

def getCurrGame(id):
  for x in gamesTable.find():
    for y in x["Players"]:
      if y == id:
        return x
  print("No players to match game code")
  return 404

def getGameData(id):
  for x in gamesTable.find():
    if x["ID"] == id:
      return x
  print("Game does not exist")
  return 404

def convertNumMonth(num):
  months = ["January", "Febuary", "March", "April", "May", "June", "July", "August", "Sepetember", "October", "November", "December"]
  return months[num-1]

def incrementDay(day, month, year):
  if month == 2 and day == 28:
    return 1, month+1, year
  elif day <= 29:
    return day+1, month, year
  elif day == 30 and (month == 9 or month == 4 or month == 6 or month == 11): #switch month
    return 1, month+1, year
  elif day == 30:
    return day+1, month, year
  elif day == 31 and month == 12: #switch year
    return 1, 1, year+1
  elif day == 31: #switch month
    return 1, month+1, year

def getFoodLbs(currGame):
  lbs = 0
  for x in currGame["Inventory"]:
    if x == "food":
      lbs = lbs + 1
  return lbs

def feedCrew(currGame):
  numFoodUsed = 0
  subtractFromScore = 0
  foodInStorage = getFoodLbs(currGame)
  if currGame["Rations"] == "filling":
    numFoodUsed = 3 * len(currGame["Players"])
  elif currGame["Rations"] == "meager":
    numFoodUsed = 2 * len(currGame["Players"])
  elif currGame["Rations"] == "bare bones":
    numFoodUsed = 1 * len(currGame["Players"])
  if numFoodUsed > foodInStorage: #not enough food
    editedList = currGame["Inventory"]
    for x in range(foodInStorage):
      editedList.remove("food")
      subtractFromScore = subtractFromScore - 1
    query = { "ID": currGame["ID"] }
    newvalues = { "$set": { "Inventory": editedList, "Score": currGame["Score"] - subtractFromScore, "HealthValue": currGame["HealthValue"] - (numFoodUsed - foodInStorage) } }
    gamesTable.update_one(query, newvalues)
  else:
    editedList = currGame["Inventory"]
    for x in range(numFoodUsed):
      editedList.remove("food")
      subtractFromScore = subtractFromScore - 1
    query = { "ID": currGame["ID"] }
    newvalues = { "$set": { "Inventory": editedList, "Score": currGame["Score"] - subtractFromScore, "HealthValue": currGame["HealthValue"] + 5*len(currGame["Players"]) } }
    gamesTable.update_one(query, newvalues)

def calculateHealth(currGame):
  healthval = currGame["HealthValue"]
  if healthval >= 50:
    return "good"
  elif healthval >= 25:
    return "poor"
  return "very poor"

def resting(currGame):
  query = { "ID": currGame["ID"] }
  newvalues = { "$set": { "HealthValue": currGame["HealthValue"] + 5*len(currGame["Players"]) } }
  gamesTable.update_one(query, newvalues)

#returns pos number and true/false boolean if it is a landmark
def nextLandmark(currPos, direction):
  nextPos = currPos + 1
  if currPos == 5 and direction == "right":
    nextPos = 11
  elif currPos == 10:
    nextPos = 22
  elif currPos == 21:
    nextPos = 33
  elif currPos == 32:
    nextPos = 41
  elif currPos == 40:
    nextPos = 32
  elif currPos == 46:
    return 0, True
  if checkpoints[nextPos][1] == "":
    return nextPos, False
  return nextPos, True

def nextLandmarkDist(currGame, direction):
  totalDist = 0
  nextPos, foundLandmark = nextLandmark(currGame["currLocation"], direction)
  while not foundLandmark:
    totalDist = totalDist + 8
    nextPos, foundLandmark = nextLandmark(nextPos, direction)
  return totalDist

def onRoadTitle(currGame):
  currPos = currGame["currLocation"]
  if not checkpoints[currPos][1] == "":
    return checkpoints[currPos][1]
  elif currPos > 0 and currPos < 5:
    return "Between Kingdom of Welic and Rushing River"
  elif currPos > 5 and currPos < 10:
    return "Between Rushing River and Harwelver"
  elif currPos > 10 and currPos < 15:
    return "Between Rushing River and Cliffs of Insanity"
  elif currPos > 15 and currPos < 21:
    return "Between Cliffs of Insanity and Dailion Keep"
  elif currPos > 21 and currPos < 25:
    return "Between Harwelver and Dragon Fortress"
  elif currPos > 25 and currPos < 32:
    return "Between Dragon Fortress and Forbidden Forest"
  elif currPos > 32 and currPos < 41:
    return "Between Dailion Keep and Forbidden Forest"
  elif currPos > 40 and currPos < 46:
    return "Between Forbidden Forest and Kingdom of Ni"

def calcNumClothes(currGame):
  count = 0
  for x in currGame["Inventory"]:
    if x == "clothes":
      count = count + 1
  return count

def calcDays(currGame):
  startDate = date(1142, currGame["RecordMonth"], 1)
  endDate = date(currGame["Year"], currGame["Month"], currGame["Day"])
  return (endDate - startDate).days

def bonuspointsLivingPlayers(currGame):
  bonus = len(currGame["Players"]) * 100
  if bonus == 500:
    bonus = bonus + 500
  return bonus

def checkLost(id):
  playersList = getGameData(id)["Players"]
  if playersList == []:
    return True
  return False

@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name='-play'))

@client.event
async def on_message(message):
    global checkpoints

    if message.author == client.user:
        return

    if(not inGame(message.author.id)):
      if message.content.lower().startswith("-play"):
        embed = discord.Embed(title="Getting Started", description="Many different people make the journey from the Kingdom of Welic to the Kingdom of Ni. (And for many reasons too: rescuing damsels in distress, joining the future dictatorship, selling fish, fighting windmills, egging the west side of the castle, etc.). You may: ")
        embed.add_field(name="[1] Be a peasant from the Valley", value="Earns the most points at the end\n")
        embed.add_field(name="[2] Be a merchant from a far off land", value="Starts with more money than peasent but less points\n")
        embed.add_field(name="[3] Be a sorcerer from the Kingdom of Ni", value="Starts with more money than merchant but less points\n")
        embed.add_field(name="[4] Be a king from the Kingdom of Welic", value="Starts with the most money\n")
        embed.set_footer(text="What is your choice?")
        await message.channel.send(content=None, embed=embed)
        gamesTable.insert_one( { "ID": ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10)), "Job": "unemployed", "Players": [message.author.id], "Money": 0, "Inventory": [], "Weather": "NA", "Pace": "steady", "Rations": "filling", "Health": "good", "HealthValue": 100, "Day": 0, "Month": 0, "Year": 0, "milesTraveled": 0, "currLocation": -4, "Score": 0, "Traveling": False, "PaceTick": False, "RationsTick": False, "RecordMonth": 0 } )
    
    else:
      if message.content.lower().startswith("-play"):
        await message.channel.send(f'{message.author} is already on the trail!')
      elif message.content.lower().startswith("-"):
        currGame = getCurrGame(message.author.id)
        if currGame["PaceTick"]:
          if message.content.lower().startswith("-1"):
            query = { "ID": currGame["ID"] }
            newvalues = { "$set": { "Pace": "steady", "PaceTick": False } }
            gamesTable.update_one(query, newvalues)
          elif message.content.lower().startswith("-2"):
            query = { "ID": currGame["ID"] }
            newvalues = { "$set": { "Pace": "strenuous", "PaceTick": False } }
            gamesTable.update_one(query, newvalues)
          elif message.content.lower().startswith("-3"):
            query = { "ID": currGame["ID"] }
            newvalues = { "$set": { "Pace": "grueling", "PaceTick": False } }
            gamesTable.update_one(query, newvalues)
          currGame = getCurrGame(message.author.id)
          # size up situation START
          heading = ""
          if checkpoints[currGame["currLocation"]][1] != "":
            heading = heading + checkpoints[currGame["currLocation"]][1] + "\n"
          heading = heading + str(currGame["Day"]) + " " + convertNumMonth(currGame["Month"]) + " " + str(currGame["Year"])
          embed = discord.Embed(title=heading, description=f'Weather: {currGame["Weather"]}\nHealth: {currGame["Health"]}\nPace: {currGame["Pace"]}\nRations: {currGame["Rations"]}')
          embed.add_field(name="[1] Continue on trail", value="\u200b\n")
          embed.add_field(name="[2] Check supplies", value="\u200b\n")
          embed.add_field(name="[4] Change pace", value="\u200b\n")
          embed.add_field(name="[5] Change food rations", value="\u200b\n")
          embed.add_field(name="[6] Stop to rest", value="\u200b\n")
          embed.set_footer(text="What is your choice?")
          await message.channel.send(content=None, embed=embed)
          # size up situation END
          return
        if currGame["RationsTick"]:
          if message.content.lower().startswith("-1"):
            query = { "ID": currGame["ID"] }
            newvalues = { "$set": { "Rations": "filling", "RationsTick": False } }
            gamesTable.update_one(query, newvalues)
          elif message.content.lower().startswith("-2"):
            query = { "ID": currGame["ID"] }
            newvalues = { "$set": { "Rations": "meager", "RationsTick": False } }
            gamesTable.update_one(query, newvalues)
          elif message.content.lower().startswith("-3"):
            query = { "ID": currGame["ID"] }
            newvalues = { "$set": { "Rations": "bare bones", "RationsTick": False } }
            gamesTable.update_one(query, newvalues)
          currGame = getCurrGame(message.author.id)
          # size up situation START
          heading = ""
          if checkpoints[currGame["currLocation"]][1] != "":
            heading = heading + checkpoints[currGame["currLocation"]][1] + "\n"
          heading = heading + str(currGame["Day"]) + " " + convertNumMonth(currGame["Month"]) + " " + str(currGame["Year"])
          embed = discord.Embed(title=heading, description=f'Weather: {currGame["Weather"]}\nHealth: {currGame["Health"]}\nPace: {currGame["Pace"]}\nRations: {currGame["Rations"]}')
          embed.add_field(name="[1] Continue on trail", value="\u200b\n")
          embed.add_field(name="[2] Check supplies", value="\u200b\n")
          embed.add_field(name="[4] Change pace", value="\u200b\n")
          embed.add_field(name="[5] Change food rations", value="\u200b\n")
          embed.add_field(name="[6] Stop to rest", value="\u200b\n")
          embed.set_footer(text="What is your choice?")
          await message.channel.send(content=None, embed=embed)
          # size up situation END
          return
        currLoc = currGame["currLocation"] 
        if currLoc == -4:
          next = False
          if message.content.lower().startswith("-1"):
            query = { "ID": currGame["ID"] }
            newvalues = { "$set": { "Job": "peasant", "Money": 1000, "currLocation": currGame["currLocation"] + 1, "Score": 400 } }
            gamesTable.update_one(query, newvalues)
            next = True
          elif message.content.lower().startswith("-2"):
            query = { "ID": currGame["ID"] }
            newvalues = { "$set": { "Job": "merchant", "Money": 2000, "currLocation": currGame["currLocation"] + 1, "Score": 300 } }
            gamesTable.update_one(query, newvalues)
            next = True
          elif message.content.lower().startswith("-3"):
            query = { "ID": currGame["ID"] }
            newvalues = { "$set": { "Job": "sorcerer", "Money": 3000, "currLocation": currGame["currLocation"] + 1, "Score": 200 } }
            gamesTable.update_one(query, newvalues)
            next = True
          elif message.content.lower().startswith("-4"):
            query = { "ID": currGame["ID"] }
            newvalues = { "$set": { "Job": "king", "Money": 4000, "currLocation": currGame["currLocation"] + 1, "Score": 100 } }
            gamesTable.update_one(query, newvalues)
            next = True
          if next:
            leader = await client.fetch_user(str(currGame["Players"][0]))
            leaderName = leader.display_name
            embed = discord.Embed(title="Gathering your Companions", description=f'The journey leader is {leaderName}. Who else is in the party?')
            embed.set_footer(text="Enter as - @user")
            await message.channel.send(content=None, embed=embed)
        elif currLoc == -3:
          if message.content.lower().startswith("-"):
            newPlayers = message.mentions
            editedList = currGame["Players"]
            numPlayers = len(editedList)
            for x in newPlayers:
              editedList.append(x.id)
              numPlayers = numPlayers + 1
              query = { "ID": currGame["ID"] }
              newvalues = { "$set": { "Players": editedList } }
              if numPlayers == 5:
                newvalues = { "$set": { "Players": editedList, "currLocation": currGame["currLocation"] + 1 } }
                embed = discord.Embed(title="Planning the Day", description=f'It is 1142. You are starting your journey at the Kingdom of Welic. You must decide which month to leave Welic.')
                embed.add_field(name="[1] March", value="The soonest date\n")
                embed.add_field(name="[2] April", value="Vegetation may be limited\n")
                embed.add_field(name="[3] May", value="Plants will be flourishing during this time\n")
                embed.add_field(name="[4] June", value="Chance it could be cool when you arrive\n")
                embed.add_field(name="[5] July", value="Might be winter before you arrive\n")
                embed.set_footer(text="What is your choice?")
                await message.channel.send(content=None, embed=embed)
              gamesTable.update_one(query, newvalues)
        elif currLoc == -2:
          next = False
          if message.content.lower().startswith("-1"):
            query = { "ID": currGame["ID"] }
            newvalues = { "$set": { "Day": 1, "Month": 3, "Year": 1142, "RecordMonth": 3, "Weather": "cold", "HealthValue": currGame["HealthValue"] - 10, "currLocation": currGame["currLocation"] + 1 } }
            gamesTable.update_one(query, newvalues)
            next = True
          elif message.content.lower().startswith("-2"):
            query = { "ID": currGame["ID"] }
            newvalues = { "$set": { "Day": 1, "Month": 4, "Year": 1142, "RecordMonth": 4, "Weather": "cold", "HealthValue": currGame["HealthValue"] - 5,  "currLocation": currGame["currLocation"] + 1 } }
            gamesTable.update_one(query, newvalues)
            next = True
          elif message.content.lower().startswith("-3"):
            query = { "ID": currGame["ID"] }
            newvalues = { "$set": { "Day": 1, "Month": 5, "Year": 1142, "RecordMonth": 5, "Weather": "warm", "currLocation": currGame["currLocation"] + 1 } }
            gamesTable.update_one(query, newvalues)
            next = True
          elif message.content.lower().startswith("-4"):
            query = { "ID": currGame["ID"] }
            newvalues = { "$set": { "Day": 1, "Month": 6, "Year": 1142, "RecordMonth": 6, "Weather": "warm", "HealthValue": currGame["HealthValue"] - 5,  "currLocation": currGame["currLocation"] + 1 } }
            gamesTable.update_one(query, newvalues)
            next = True
          elif message.content.lower().startswith("-5"):
            query = { "ID": currGame["ID"] }
            newvalues = { "$set": { "Day": 1, "Month": 7, "Year": 1142, "RecordMonth": 7, "Weather": "warm", "HealthValue": currGame["HealthValue"] - 10, "currLocation": currGame["currLocation"] + 1 } }
            gamesTable.update_one(query, newvalues)
            next = True
          if next:
            embed = discord.Embed(title="Rations and Supplies", description=f'Before beginning your journey, you should buy equipment and supplies. You have {currGame["Money"]} airgeads, but you don\'t have to spend it all now. You can buy whatever you need at Anastasia\'s shop.')
            await message.channel.send(content=None, embed=embed)

            embed = discord.Embed(title="Message from Anastasia", description=f'*Hello, I\'m Anastasia. So you are going to Ni? I can fix you up with what you need:*')
            embed.add_field(name="- a mighty stead", value="You will need one per person\n")
            embed.add_field(name="- clothing for both summer and winter", value="It will be hot and cold on your journey\n")
            embed.add_field(name="- food", value="Be sure to pack enough for everyone\n")
            embed.add_field(name="- weapons", value="There be dragons\n")
            embed.set_footer(text="Press - to continue")
            await message.channel.send(content=None, embed=embed)
        elif currLoc == -1:
          if message.content.lower().startswith("-1"):
            if currGame["Money"] >= 50:
              editedList = currGame["Inventory"]
              editedList.append("horse")
              query = { "ID": currGame["ID"] }
              newvalues = { "$set": { "Money": currGame["Money"] - 50, "Inventory": editedList } }
              gamesTable.update_one(query, newvalues)
          elif message.content.lower().startswith("-2"):
            if currGame["Money"] >= 5:
              editedList = currGame["Inventory"]
              editedList.append("clothes")
              query = { "ID": currGame["ID"] }
              newvalues = { "$set": { "Money": currGame["Money"] - 5, "Inventory": editedList } }
              gamesTable.update_one(query, newvalues)
          elif message.content.lower().startswith("-3"):
            if currGame["Money"] >= 20:
              editedList = currGame["Inventory"]
              for i in range(20):
                editedList.append("food")
              query = { "ID": currGame["ID"] }
              newvalues = { "$set": { "Money": currGame["Money"] - 20, "Inventory": editedList } }
              gamesTable.update_one(query, newvalues)
          elif message.content.lower().startswith("-4"):
            if currGame["Money"] >= 20:
              editedList = currGame["Inventory"]
              editedList.append("armor")
              query = { "ID": currGame["ID"] }
              newvalues = { "$set": { "Money": currGame["Money"] - 20, "Inventory": editedList } }
              gamesTable.update_one(query, newvalues)
          elif message.content.lower().startswith("-5"):
            if currGame["Money"] >= 10:
              editedList = currGame["Inventory"]
              editedList.append("sword")
              query = { "ID": currGame["ID"] }
              newvalues = { "$set": { "Money": currGame["Money"] - 10, "Inventory": editedList } }
              gamesTable.update_one(query, newvalues)
          if message.content.lower().startswith("-6"):
            query = { "ID": currGame["ID"] }
            newvalues = { "$set": { "currLocation": currGame["currLocation"] + 1 } }
            gamesTable.update_one(query, newvalues)
            #display next message
            embed = discord.Embed(title="Message from Anastasia", description=f'*Well then, you are ready to start. Good luck! You have a long and difficult journey ahead of you.*')
            await message.channel.send(content=None, embed=embed)
            embed = discord.Embed(title="Kingdom of Welic", description=f'{currGame["Day"]} {convertNumMonth(currGame["Month"])} {currGame["Year"]}')
            await message.channel.send(content=None, embed=embed)
            query = { "ID": currGame["ID"] }
            newvalues = { "$set": { "Traveling": False, } }
            gamesTable.update_one(query, newvalues)
            currGame = getCurrGame(message.author.id)
            # size up situation START
            heading = ""
            if checkpoints[currGame["currLocation"]][1] != "":
              heading = heading + checkpoints[currGame["currLocation"]][1] + "\n"
            heading = heading + str(currGame["Day"]) + " " + convertNumMonth(currGame["Month"]) + " " + str(currGame["Year"])
            embed = discord.Embed(title=heading, description=f'Weather: {currGame["Weather"]}\nHealth: {currGame["Health"]}\nPace: {currGame["Pace"]}\nRations: {currGame["Rations"]}')
            embed.add_field(name="[1] Continue on trail", value="\u200b\n")
            embed.add_field(name="[2] Check supplies", value="\u200b\n")
            embed.add_field(name="[4] Change pace", value="\u200b\n")
            embed.add_field(name="[5] Change food rations", value="\u200b\n")
            embed.add_field(name="[6] Stop to rest", value="\u200b\n")
            embed.set_footer(text="What is your choice?")
            await message.channel.send(content=None, embed=embed)
            # size up situation END
            return

          currGame = getCurrGame(message.author.id)
          embed = discord.Embed(title="Anastasia\'s Shop", description=f'Amount you have: {currGame["Money"]} airgeads')
          embed.add_field(name="[1] Horse", value="50 airgeads\n")
          embed.add_field(name="[2] Clothing", value="5 airgeads/set\n")
          embed.add_field(name="[3] Food", value="1 airgeads/lb (sold in 20 lb increments)\n")
          embed.add_field(name="[4] Armor", value="20 airgeads\n")
          embed.add_field(name="[5] Sword", value="10 airgeads\n")
          embed.add_field(name="[6] Exit", value="Ready to start?\n")
          embed.set_footer(text="Which item would you like to buy?")
          await message.channel.send(content=None, embed=embed) 
        elif currLoc >= 0:
          if message.content.lower().startswith("-1"):
            query = { "ID": currGame["ID"] }
            newvalues = { "$set": { "Traveling": True, } }
            gamesTable.update_one(query, newvalues)
            currGame = getCurrGame(message.author.id)
            # Update the values
            addPoints = 0
            deductHealth = 0
            if currGame["Day"] % 2 == 0:
              feedCrew(currGame)
            newWeather = random.choice(["warm", "cold"])
            warmthness = calcNumClothes(currGame) - len(currGame["Players"])
            if warmthness < 0:
              deductHealth = 5*warmthness
            newDay, newMonth, newYear = incrementDay(currGame["Day"], currGame["Month"], currGame["Year"])
            newHealth = calculateHealth(currGame)
            # death check START
            if currGame["HealthValue"] < 0:
              editedListPlayers = currGame["Players"]
              dead = await client.fetch_user(str(editedListPlayers[len(editedListPlayers)-1]))
              deadName = dead.display_name
              editedListPlayers.remove(editedListPlayers[len(editedListPlayers)-1])
              embed = discord.Embed(title=f'{deadName} has died.', description=f'')
              await message.channel.send(content=None, embed=embed)
              query = { "ID": currGame["ID"] }
              newvalues = { "$set": { "Players": editedListPlayers } }
              gamesTable.update_one(query, newvalues)
              if checkLost(currGame["ID"]):
                embed = discord.Embed(title=f'Bring out yer dead!', description=f'All travelers have perished.')
                await message.channel.send(content=None, embed=embed)
                print("game ended - deleteing entry in db")
                query = { "ID": currGame["ID"] }
                gamesTable.delete_one(query)
                return
            # death check END
            newLoc, _ = nextLandmark(currGame["currLocation"], "nan")
            if currGame["Pace"] == "strenuous":
              addPoints = addPoints + 1
              deductHealth = deductHealth + 1
            elif currGame["Pace"] == "grueling":
              addPoints = addPoints + 2
              deductHealth = deductHealth + 2
            query = { "ID": currGame["ID"] }
            newvalues = { "$set": { "Day": newDay, "Month": newMonth, "Year": newYear, "Weather": newWeather, "Health": newHealth, "HealthValue": currGame["HealthValue"] - deductHealth, "milesTraveled": currGame["milesTraveled"]+8, "currLocation": newLoc, "Score": currGame["Score"] + addPoints } }
            gamesTable.update_one(query, newvalues)
            # end of sec
            while currGame["Traveling"]:
              currGame = getCurrGame(message.author.id)
              #directionFork = random.choice(["left", "right"])
              # traveling stats START
              embed = discord.Embed(title="On the Road", description=f'{onRoadTitle(currGame)}')
              embed.add_field(name="Date", value=f'{str(currGame["Day"])} {convertNumMonth(currGame["Month"])} {str(currGame["Year"])}\n')
              embed.add_field(name="Weather", value=f'{currGame["Weather"]}\n')
              embed.add_field(name="Health", value=f'{str(currGame["Health"])}\n')
              embed.add_field(name="Food", value=f'{str(getFoodLbs(currGame))} pounds\n')
              embed.add_field(name="Next Landmark", value=f'{nextLandmarkDist(currGame, random.choice(["left", "right"]))} miles\n')
              embed.add_field(name="Miles Traveled", value=f'{str(currGame["milesTraveled"])} miles\n')
              embed.set_footer(text="Press - to size up the situation")
              await message.channel.send(content=None, embed=embed)
              # traveling stats END
              # random accident START
              if random.choice([True, False, False]):
                namePicked = random.choice(currGame["Players"])
                victum = await client.fetch_user(str(namePicked))
                victumName = victum.display_name
                numPlayers = len(currGame["Players"])
                #second parameter affects health
                accidentMessage = random.choice([
                  (f'{victumName} has dysentery.', 5, None, None),
                  (f'Everyone has dysentery.', 5*numPlayers, None, None),
                  (f'{victumName} has leprosy.', 5, None, None),
                  (f'Everyone has the plague.', 5*numPlayers, None, None),
                  (f'{victumName} has the plague.', 5, None, None),
                  (f'{victumName} has The Black Death.', 5, None, None),
                  (f'{victumName} has typhoid.', 5, None, None),
                  (f'{victumName} has cholera.', 5, None, None),
                  (f'{victumName} has chicken pox.', 5, None, None),
                  (f'{victumName} has measles.', 5, None, None),
                  (f'Everyone has chicken pox.', 5*numPlayers, None, None),
                  (f'Everyone has measles.', 5*numPlayers, None, None),
                  (f'{victumName} has been eaten by a dragon ({victumName} has died).', 0, namePicked, None),
                  (f'{victumName} has died.', 0, namePicked, None),
                  (f'{victumName} has been stabbed by a passing knight.', 5, None, None),
                  (f'{victumName} has been beaten senseless by Don Quixote (the ingenious gentleman received just as equal of a beating in return).', 5, None, None),
                  (f'{victumName} has been cursed.', 5, None, None),
                  (f'Everyone has been cursed.', 5*numPlayers, None, None),
                  (f'{victumName} has fallen from their horse.', 5, None, None),
                  (f'{victumName} has been bitten by a rabid... something.', 5, None, None),
                  (f'A horse ran away.', 0, None, "horse"),
                  (f'{victumName} lost some of the supplies.', 0, None, "clothes"),
                  (f'{victumName} lost some of the supplies.', 0, None, "armor"),
                  (f'{victumName} lost some of the supplies.', 0, None, "sword"),
                  (f'A horse was stolen.', 0, None, "horse"),
                ])
                #deal with consequences
                displayMessage = True
                newHealth = currGame["HealthValue"]
                editedListPlayers = currGame["Players"]
                editedListInventory = currGame["Inventory"]
                newScore = currGame["Score"]
                if accidentMessage[1] > 0:
                  newHealth = newHealth - accidentMessage[1]
                if not accidentMessage[2] == None:
                  editedListPlayers.remove(accidentMessage[2])
                  query = { "ID": currGame["ID"] }
                  newvalues = { "$set": { "Players": editedListPlayers } }
                  gamesTable.update_one(query, newvalues)
                  if checkLost(currGame["ID"]):
                    embed = discord.Embed(title=f'Bring out yer dead!', description=f'All travelers have perished.')
                    await message.channel.send(content=None, embed=embed)
                    print("game ended - deleteing entry in db")
                    query = { "ID": currGame["ID"] }
                    gamesTable.delete_one(query)
                    return
                if not accidentMessage[3] == None:
                  if accidentMessage[3] in editedListInventory:
                    editedListInventory.remove(accidentMessage[3])
                    newScore = newScore - 50
                  else:
                    displayMessage = False
                query = { "ID": currGame["ID"] }
                newvalues = { "$set": { "HealthValue": newHealth, "Players": editedListPlayers, "Inventory": editedListInventory, "Score": newScore } }
                gamesTable.update_one(query, newvalues)
                if displayMessage:
                  embed = discord.Embed(title=f'{accidentMessage[0]}', description=f'')
                  await message.channel.send(content=None, embed=embed)
              # random accident END
              if not checkpoints[currGame["currLocation"]][1] == "" and currGame["currLocation"] > 0: #it's a landmark
                embed = discord.Embed(title=f'{checkpoints[currGame["currLocation"]][1]}', description=f'{currGame["Day"]} {convertNumMonth(currGame["Month"])} {currGame["Year"]}')
                embed.set_footer(text="Press - to continue")
                await message.channel.send(content=None, embed=embed)
                break
              #update the values
              addPoints = 0
              deductHealth = 0
              if currGame["Day"] % 2 == 0:
                feedCrew(currGame)
              newWeather = random.choice(["warm", "cold"])
              warmthness = calcNumClothes(currGame) - len(currGame["Players"])
              if warmthness < 0:
                deductHealth = 5*abs(warmthness)
              newDay, newMonth, newYear = incrementDay(currGame["Day"], currGame["Month"], currGame["Year"])
              newHealth = calculateHealth(currGame)
              # death check START
              if currGame["HealthValue"] < 0:
                editedListPlayers = currGame["Players"]
                dead = await client.fetch_user(str(editedListPlayers[len(editedListPlayers)-1]))
                deadName = dead.display_name
                editedListPlayers.remove(editedListPlayers[len(editedListPlayers)-1])
                #currGame = getCurrGame(message.author.id)
                embed = discord.Embed(title=f'{deadName} has died.', description=f'')
                await message.channel.send(content=None, embed=embed)
                query = { "ID": currGame["ID"] }
                newvalues = { "$set": { "Players": editedListPlayers } }
                gamesTable.update_one(query, newvalues)
                if checkLost(currGame["ID"]):
                  embed = discord.Embed(title=f'Bring out yer dead!', description=f'All travelers have perished.')
                  await message.channel.send(content=None, embed=embed)
                  print("game ended - deleteing entry in db")
                  query = { "ID": currGame["ID"] }
                  gamesTable.delete_one(query)
                  return
              # death check END
              newLoc, _ = nextLandmark(currGame["currLocation"], "nan")
              if currGame["Pace"] == "strenuous":
                addPoints = addPoints + 1
                deductHealth = deductHealth + 1
              elif currGame["Pace"] == "grueling":
                addPoints = addPoints + 2
                deductHealth = deductHealth + 2
              query = { "ID": currGame["ID"] }
              newvalues = { "$set": { "Day": newDay, "Month": newMonth, "Year": newYear, "Weather": newWeather, "Health": newHealth, "HealthValue": currGame["HealthValue"] - deductHealth, "milesTraveled": currGame["milesTraveled"]+8, "currLocation": newLoc, "Score": currGame["Score"] + addPoints } }
              gamesTable.update_one(query, newvalues)
          elif message.content.lower().startswith("-2"): #check supplies
            embed = discord.Embed(title="Your Supplies", description=f'')
            numHorses = 0
            numArmor = 0
            numSwords = 0
            numClothes = 0
            lbsFood = getFoodLbs(currGame)
            for x in currGame["Inventory"]:
              if x == "horse": numHorses = numHorses + 1
              elif x == "armor": numArmor = numArmor + 1
              elif x == "sword": numSwords = numSwords + 1
              elif x == "clothes": numClothes = numClothes + 1
            embed.add_field(name="horses", value=f'{numHorses}\n')
            embed.add_field(name="sets of clothing", value=f'{numClothes}\n')
            embed.add_field(name="sets of armor", value=f'{numArmor}\n')
            embed.add_field(name="swords", value=f'{numSwords}\n')
            embed.add_field(name="pounds of food", value=f'{lbsFood}\n')
            embed.add_field(name="money left", value=f'{currGame["Money"]}\n')
            embed.set_footer(text="Press - to continue")
            await message.channel.send(content=None, embed=embed)
          elif message.content.lower().startswith("-4"): #pace option
            embed = discord.Embed(title="Change Pace", description=f'The pace at which you travel can change. Your choices are:')
            embed.add_field(name="[1] a steady pace", value="You travel about 8 hours a day, taking frequent rests. You take care not to get too tired.\n")
            embed.add_field(name="[2] a strenuous pace", value="You travel about 12 hours a day, starting just after sunrise and stopping shortly before sunset. You stop to rest only when necessary. You finish each day feeling very tired.\n")
            embed.add_field(name="[3] a grueling pace", value="You travel about 16 hours a day, starting before sunrise and continuing until dark. You almost never stop to rest. You do not get enough sleep at night. You finish each day feeling absolutely exhauseted, and your health suffers.\n")
            embed.set_footer(text="What is your choice?")
            await message.channel.send(content=None, embed=embed)
            query = { "ID": currGame["ID"] }
            newvalues = { "$set": { "PaceTick": True } }
            gamesTable.update_one(query, newvalues)
          elif message.content.lower().startswith("-5"): #rations option
            embed = discord.Embed(title="Change Food Rations", description=f'The amount of food the people in your party eat each day can change. These amounts are:')
            embed.add_field(name="[1] filling", value="Meals are large and generous.\n")
            embed.add_field(name="[2] meager", value="Meals are small, but adequate.\n")
            embed.add_field(name="[3] bare bones", value="Meals are very small; everyone stays hungry.\n")
            embed.set_footer(text="What is your choice?")
            await message.channel.send(content=None, embed=embed)
            query = { "ID": currGame["ID"] }
            newvalues = { "$set": { "RationsTick": True } }
            gamesTable.update_one(query, newvalues)
          elif message.content.lower().startswith("-6"): #rest option
            embed = discord.Embed(title="Resting", description=f'You have rested for a day')
            await message.channel.send(content=None, embed=embed)
            resting(currGame)
            newDay, newMonth, newYear = incrementDay(currGame["Day"], 
            currGame["Month"], currGame["Year"])
            newHealth = calculateHealth(currGame)
            # death check START
            if currGame["HealthValue"] < 0:
              editedListPlayers = currGame["Players"]
              dead = await client.fetch_user(str(editedListPlayers[len(editedListPlayers)-1]))
              deadName = dead.display_name
              editedListPlayers.remove(editedListPlayers[len(editedListPlayers)-1])
              embed = discord.Embed(title=f'{deadName} has died.', description=f'')
              await message.channel.send(content=None, embed=embed)
              query = { "ID": currGame["ID"] }
              newvalues = { "$set": { "Players": editedListPlayers } }
              gamesTable.update_one(query, newvalues)
              if checkLost(currGame["ID"]):
                embed = discord.Embed(title=f'Bring out yer dead!', description=f'All travelers have perished.')
                await message.channel.send(content=None, embed=embed)
                print("game ended - deleteing entry in db")
                query = { "ID": currGame["ID"] }
                gamesTable.delete_one(query)
                return
            # death check END
            query = { "ID": currGame["ID"] }
            newvalues = { "$set": { "Day": newDay, "Month": newMonth, "Year": newYear, "Health": newHealth, "Score": currGame["Score"]-1 } }
            gamesTable.update_one(query, newvalues)
            currGame = getCurrGame(message.author.id)
            # size up situation START
            heading = ""
            if checkpoints[currGame["currLocation"]][1] != "":
              heading = heading + checkpoints[currGame["currLocation"]][1] + "\n"
            heading = heading + str(currGame["Day"]) + " " + convertNumMonth(currGame["Month"]) + " " + str(currGame["Year"])
            embed = discord.Embed(title=heading, description=f'Weather: {currGame["Weather"]}\nHealth: {currGame["Health"]}\nPace: {currGame["Pace"]}\nRations: {currGame["Rations"]}')
            embed.add_field(name="[1] Continue on trail", value="\u200b\n")
            embed.add_field(name="[2] Check supplies", value="\u200b\n")
            embed.add_field(name="[4] Change pace", value="\u200b\n")
            embed.add_field(name="[5] Change food rations", value="\u200b\n")
            embed.add_field(name="[6] Stop to rest", value="\u200b\n")
            embed.set_footer(text="What is your choice?")
            await message.channel.send(content=None, embed=embed)
            # size up situation END

          elif message.content.lower().startswith("-"):
            query = { "ID": currGame["ID"] }
            newvalues = { "$set": { "Traveling": False, } }
            gamesTable.update_one(query, newvalues)
            currGame = getCurrGame(message.author.id)
            # size up situation START
            heading = ""
            if checkpoints[currGame["currLocation"]][1] != "":
              heading = heading + checkpoints[currGame["currLocation"]][1] + "\n"
            heading = heading + str(currGame["Day"]) + " " + convertNumMonth(currGame["Month"]) + " " + str(currGame["Year"])
            embed = discord.Embed(title=heading, description=f'Weather: {currGame["Weather"]}\nHealth: {currGame["Health"]}\nPace: {currGame["Pace"]}\nRations: {currGame["Rations"]}')
            embed.add_field(name="[1] Continue on trail", value="\u200b\n")
            embed.add_field(name="[2] Check supplies", value="\u200b\n")
            embed.add_field(name="[4] Change pace", value="\u200b\n")
            embed.add_field(name="[5] Change food rations", value="\u200b\n")
            embed.add_field(name="[6] Stop to rest", value="\u200b\n")
            embed.set_footer(text="What is your choice?")
            await message.channel.send(content=None, embed=embed)
            # size up situation END

          if currGame["currLocation"] == 46:
            #gameEnd
            embed = discord.Embed(title="The End", description=f'Congratulations! You have made it to the Kingdom of Ni! Let\'s see how many points you have received.')
            await message.channel.send(content=None, embed=embed)
            embed = discord.Embed(title="Score", description=f'{currGame["Score"] + (100-calcDays(currGame)) + currGame["HealthValue"] + currGame["Money"] + bonuspointsLivingPlayers(currGame)}')
            await message.channel.send(content=None, embed=embed)
            print("game ended - deleteing entry in db")
            query = { "ID": currGame["ID"] }
            gamesTable.delete_one(query)
            return

  

server.runServer()
client.run(os.environ['TOKEN'])
