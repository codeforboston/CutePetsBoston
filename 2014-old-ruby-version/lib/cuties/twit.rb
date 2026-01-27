require 'twitter'
require 'logger'
require 'pp'
require 'open-uri'

class Twit
  attr_reader :pet

  def initialize(pet)
    @pet = pet

    @errlog       = Logger.new(STDERR)
    @errlog.level = Logger::WARN #set to Logger:WARN to avoid seing status messages
  end

  def greeting
    Greeting.random
  end

  def message
    "#{greeting} #{pet.message}"
  end


  def client
    Twitter::REST::Client.new do |config|
      begin
        config.consumer_key        = ENV.fetch('consumer_key')
        config.consumer_secret     = ENV.fetch('consumer_secret')
        config.access_token        = ENV.fetch('access_token')
        config.access_token_secret = ENV.fetch('access_token_secret')

      rescue KeyError
        @errlog.error "What are your twitter keys? I see none in env. Did you read the README? Specifically,git  #{$!}"
      end

    end
  end


  def tweet
    unless pet.pic.nil?
      uri   = URI.parse(pet.pic)
      media = uri.open
      print message
      client.update_with_media(message, media)
    else
      client.update(message)
    end
  end

end
