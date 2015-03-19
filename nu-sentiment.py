#!/usr/bin/env python
__author__ = 'cryptoassure'

# scope: fetch shareholder sentiment (vote counts for motions and grants)

import time
import datetime
import requests
from PIL import Image, ImageFont, ImageDraw, ImageColor, ImageFilter

# logging
import os
import logging

# Directory where the files need to end up
logDir = os.path.abspath(os.path.join(os.getcwd()))
logFile = os.path.join(logDir,'status.log')

logging.basicConfig(filename=logFile,level=logging.DEBUG,
        format="[%(levelname)s] %(asctime)s.%(msecs)dGMT %(module)s - %(funcName)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
logging.Formatter.converter = time.gmtime

logging.info("STARTING...")
start_time = time.time() # timer for debugging

# Nu historical data lookup API routes
url_base = "http://nu.mj2p.co.uk/nu-historical-data"
motions_route = "?cmd=getmotions"
grants_route = "?cmd=getcustodianvotes"

# time variables 
now = int(datetime.datetime.now().strftime('%s'))
timeframe = 600 # we only care about the most recent block's votes, but grab a larger window than needed and then only use the latest object's values (prevents situations where a block hasn't been found in over a minute)
sentiment_timeframe = int(now - (timeframe))

# take the calculated unix epoch from sentiment_timeframe and generate
# a UTC datetime string formatted to how the API wants the "frm=" date;
# we want this format: '2015-03-15%2021:53:26'
# note: '%20' is the url parameter representation of a non-breaking space

get_from = "&frm=" + (datetime.datetime.utcfromtimestamp(sentiment_timeframe).strftime('%Y-%m-%d %H:%M:%S')).replace(" ", "%20")

# --- FUNCTIONS ----
def generateMotionImage(motion_hash, block_percentage, shareday_percentage):
  
  # create new image
  multi = 2
  imgx = 75 * multi # image width in pixels
  imgy = 45 * multi # image height in pixels
  image = Image.new('RGBA', (imgx, imgy), (255, 160, 160, 5))

  draw = ImageDraw.Draw(image)

  font = ImageFont.truetype('fonts/CourierPrimeBold.ttf', (24 * multi))
  label_font = ImageFont.truetype('fonts/CourierPrime.ttf', (12 * multi))
  small_font = ImageFont.truetype('fonts/CourierPrimeBold.ttf', (16 * multi))

  # generate strings
  blockpct_int = str(int(block_percentage))
  blockpct_decimal = str(block_percentage % 1).replace("0.", "")

  # if either value only has one digit, normalize
  if len(blockpct_int) == 1:
    blockpct_int = "0" + blockpct_int
  if len(blockpct_decimal) == 1:
    blockpct_decimal = blockpct_decimal + "0"

  # draw the label
  draw.text(((11.5 * multi),(5* multi)), "SUPPORT", font=label_font, fill=(0,116,160))
  # draw the block percentage indicator (int)
  draw.text(((4  * multi),(21 * multi)), blockpct_int, font=font, fill=(0,116,160))
  # draw the decimal point
  draw.text(((30 * multi),(26 * multi)), ".", font=small_font, fill=(0,116,160))

  # draw the block percentage indicator (decimal)
  # adjust vertical positioning if the decimal string contains a '9'
  if '9' in blockpct_decimal:
    draw.text(((38 * multi),((27 * multi) - 1)), blockpct_decimal, font=small_font, fill=(0,116,160,96))
  else:
    draw.text(((38 * multi),(26 * multi)), blockpct_decimal, font=small_font, fill=(0,116,160,96))

  # draw the percentage sign
  draw.text(((60 * multi),(26 * multi)), "%", font=small_font, fill=(0,116,160))

  image.save(("assets/motion_%s.png"%(motion_hash)), "PNG")



def generateGrantImage(address, nbt_value, gblock_percentage, gshareday_percentage):
  
  # create new image
  multi = 2
  imgx = 75 * multi # image width in pixels
  imgy = 45 * multi # image height in pixels
  image = Image.new('RGBA', (imgx, imgy), (255, 160, 160, 5))

  draw = ImageDraw.Draw(image)

  font = ImageFont.truetype('fonts/CourierPrimeBold.ttf', (24 * multi))
  label_font = ImageFont.truetype('fonts/CourierPrime.ttf', (12 * multi))
  small_font = ImageFont.truetype('fonts/CourierPrimeBold.ttf', (16 * multi))

  # generate strings
  blockpct_int = str(int(gblock_percentage))
  blockpct_decimal = str(gblock_percentage % 1).replace("0.", "")
  nbt_value = str(nbt_value).replace(".", "_")

  # if either value only has one digit, normalize
  if len(blockpct_int) == 1:
    blockpct_int = "0" + blockpct_int
  if len(blockpct_decimal) == 1:
    blockpct_decimal = blockpct_decimal + "0"

  # draw the label
  draw.text(((11.5 * multi),(5* multi)), "SUPPORT", font=label_font, fill=(0,116,160))
  # draw the block percentage indicator (int)
  draw.text(((4  * multi),(21 * multi)), blockpct_int, font=font, fill=(0,116,160))
  # draw the decimal point
  draw.text(((30 * multi),(26 * multi)), ".", font=small_font, fill=(0,116,160))

  # draw the block percentage indicator (decimal)
  # adjust vertical positioning if the decimal string contains a '9'
  if '9' in blockpct_decimal:
    draw.text(((38 * multi),((27 * multi) - 1)), blockpct_decimal, font=small_font, fill=(0,116,160,96))
  else:
    draw.text(((38 * multi),(26 * multi)), blockpct_decimal, font=small_font, fill=(0,116,160,96))

  # draw the percentage sign
  draw.text(((60 * multi),(26 * multi)), "%", font=small_font, fill=(0,116,160))

  image.save(("assets/grant_%s.png"%(address)), "PNG")



# ---- PROCESS MOTION & GRANT VOTES ----
# retrieve data and build objects that we can pull values from
try:
  r = requests.get(url_base)
  
  # check to make sure the end point is available; if it is, proceed...
  logging.info("Checking status of nu-historical-data endpoint...")
  if r.status_code == requests.codes.ok:
    logging.info("%s - API is reachable. Retrieving data for active motions..." % (r.status_code))

    # --- MOTIONS ---
    # get the vote data for the active motions
    motions = ("%s%s%s" %(url_base, motions_route, get_from))
    get_motions = requests.get(motions)
    motions_json = get_motions.json()

    # get the count of the number of records returned and then use that to
    # grab the latest set of motion votes in the block chain
    num_records = motions_json['number_of_records']
    last_record = (num_records - 1)
    latest_motions = motions_json['data'][last_record]['value']

    #print latest_motions

    motionlist = []
    motionlist = latest_motions.keys()

    for motion in motionlist:
      # set up variables for each graphic
      motion_hash = motion
      blocks = latest_motions[motion]['blocks']
      block_percentage = latest_motions[motion]['block_percentage']
      sharedays = latest_motions[motion]['sharedays']
      shareday_percentage = latest_motions[motion]['shareday_percentage']

      logging.info("Creating graphic for active motion: %s (Blocks: %s, Block Pct: %s, SDD: %s, SDD Pct: %s)" % (motion_hash, blocks, block_percentage, sharedays, shareday_percentage))

      # build graphic from motion statistics
      generateMotionImage(motion_hash, block_percentage, shareday_percentage)

    logging.info("Motions completed. Starting on custodian grant voting...")

    # TODO: Review list of files in directory and confirm that
    # the hash appears in the current block; if not, and a file exists
    # set the file's vote value '0.0%'

    # --- GRANTS ---
    # get the vote data for the active grants
    grants = ("%s%s%s" %(url_base, grants_route, get_from))
    get_grants = requests.get(grants)
    grants_json = get_grants.json()

    # get the count of the number of records returned and then use that to
    # grab the latest set of motion votes in the block chain
    num_records = grants_json['number_of_records']
    last_record = (num_records - 1)
    latest_grants = grants_json['data'][last_record]['value']

    #print latest_grants

    grantlist = []
    grantlist = latest_grants.keys()
    
    # disregard the 'total' object that isn't supposed to be in the 
    # grant address list, but that is added by the nu-historical-data API
    grantlist.remove('total')

    for grant in grantlist:

      # set 'gblock' and 'gblock_percentage' variables to zero so they can
      # used inside of the next iterative step
      gblock = 0
      gblock_percentage = 0
      gsharedays = 0
      gshareday_percentage = 0

      # setup variables for each graphic
      address = grant

      # check to see how many 'amount' leaves are listed under each address;
      # if it's more than one, check to see which one has a larger block count
      # and make the educated guess that this is the right one (the rest being)
      # incorrectly entered values in a Nu shareholder's client
      amountlist = []
      amountlist = latest_grants[grant].keys()

      #print amountlist

      # check each's block count and keep the largest
      for amount in amountlist:

        if gblock == 0:
          # first iteration
          nbt_value = amount
          gblock = latest_grants[grant][amount]['blocks']
          gblock_percentage = latest_grants[grant][amount]['block_percentage']
          gsharedays = latest_grants[grant][amount]['sharedays']
          gshareday_percentage = latest_grants[grant][amount]['shareday_percentage']

        
        else:
          nbt_value_tmp = amount
          gblock_tmp = latest_grants[grant][nbt_value_tmp]['blocks']
          gblock_percentage_tmp = latest_grants[grant][nbt_value_tmp]['block_percentage']
          gsharedays_tmp = latest_grants[grant][nbt_value_tmp]['sharedays']
          gshareday_percentage_tmp = latest_grants[grant][nbt_value_tmp]['shareday_percentage']

          if gblock_tmp > gblock:
            nbt_value = nbt_value_tmp
            gblock = gblock_tmp
            gblock_percentage = gblock_percentage_tmp
            gsharedays = gsharedays_tmp
            gshareday_percentage = gshareday_percentage_tmp

      logging.info("Creating graphic for active grant proposal: %s | %s (Blocks: %s, Block Pct: %s, SDD: %s, SDD Pct: %s)" % (address, nbt_value, blocks, block_percentage, sharedays, shareday_percentage))

      # generate graphic from grant statistics
      generateGrantImage(address, nbt_value, gblock_percentage, gshareday_percentage)

      logging.info("Grants completed. Finishing up...")

except Exception, e:
  print e

logging.info("FINISHED. Total processing time: %s seconds.\n\n" % (time.time() - start_time))