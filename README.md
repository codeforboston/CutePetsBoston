CutiesInBoston
==============

Post a random adoptable pet from the Boston MSPCA to a twitter feed.

Project of [Becky Boone](https://github.com/boonrs) and [Drew](https://github.com/drewrwilson) during their fellowship at Code for America in 2014.

Modified by [CodeforBoston](codeforboston.com) to work with the Petfinder.com API

## Heroku Deploy

[![Deploy](https://www.herokucdn.com/deploy/button.png)](https://heroku.com/deploy)

## About

A twitter bot that pulls data from the Petfinder API and tweets out adoptable pets from the [Boston MSPCA](http://www.mspca.org/adoption/boston/).

It should be easily extendable to other shelters using petfinder.com to list their animals.

**Links to API and Bot**

* [Twitter bot](http://twitter.com/CutiesInBoston)

* [API Docs`](https://www.petfinder.com/developers/api-docs)

## Setup

### Install dependencies (other gems, aka Ruby libraries)

    bundle install

### Get your API keys

You need to sign up for a twitter API. You'll need all of the following:

* consumer_key
* consumer_secret
* access_token
* access_token_secret

You'll also need Petfinder keys

* petfinder_key
* petfinder_secret

To get them, first register for a Petfinder account: https://users.petfinder.com/login

Then sign up for the API keys: https://www.petfinder.com/developers/api-key


### Set up your environment variables

We use dotenv to manage environment variables. When you have your keys, add them to a new file saved as `.env`. Make sure to include the preceding `.`. Mac OS X will warn you about creating a dotfile, but no worries, all the cool kids are doing it.

However, make sure that there is a line `.env` in your `.gitignore` before staging or committing any changes. Never commit environment variables.

    consumer_key=XXXXXXXXXXXXXXXXXXXXXX
    consumer_secret=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
    access_token=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
    access_token_secret=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
    petfinder_key=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
    petfinder_secret=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

If you don't want to deal with `.env`, you could run the following every time you open a new Terminal session, or store them in your `~/.bash_profile`.

    export consumer_key=XXXXXXXXXXXXXXXXXXXXXX
    export consumer_secret=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
    export access_token=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
    export access_token_secret=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
    export petfinder_key=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
    export petfinder_secret=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

### How to Tweet

    rake tweet

The tweet task is in the Rakefile, which invokes the rest of `cuties.rb`.

### How to Tweet Periodically

CutiesInDenver uses Heroku and the Heroku Scheduler plugin to tweet at regular intervals.

    cd #{current_path}; git fetch origin; git reset --hard #{branch}

If you already have a server and have pulled the bot from github add the following to your crontab (using crontab -e)

This tweets at 8:00am and 4:00pm every day.

    00 08,16 * * * cd /path/to/cuties && /usr/local/bin/rake tweet

-----------------------

**Hat tips**

* Kudos to [Darius](https://github.com/dariusk) for his [great guide](http://tinysubversions.com/2013/09/how-to-make-a-twitter-bot/) on how to make a twitter bot.

* And kudo to [Erik](https://github.com/sferik/) for the [twitter gem](https://github.com/sferik/twitter).
