require 'dotenv'
Dotenv.load

require_relative 'lib/cuties'

desc "Tweet random pet."
task :tweet do
  Twit.new(AdoptAPet.random).tweet
end

task :default => :twitter
