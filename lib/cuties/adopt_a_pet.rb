require 'net/http'
require 'json'
require 'open-uri'
require 'pp'

require 'dotenv'
Dotenv.load

module AdoptAPet
  URL = 'http://api.petfinder.com/pet.getRandom'

  PARAMS = {
    format:    'json',
    key:        ENV.fetch('petfinder_key'),
    shelterid: 'MA38', # MSPCA in Jamaica Plain
    output:    'full'
  }

  SEXES = { m: 'male', f: 'female' }

  def self.random
    pet = fetch_pet while pet.nil? || pet.error?
    pet
  end

  private


  def self.get_breeds(pet)
    breeds = [pet['breeds']['breed']].flatten  # Coerces into an Array
    breeds.map{ |b| b["$t"] }
  end


  def self.get_photo(pet)
    # Assume that if there isn't a 3rd photo, there is a first one
    # There's some more refactoring to be done here.

    unless pet['media']['photos']['photo'].nil?
      photo = pet['media']['photos']['photo'][2] || pet['media']['photos']['photo'][0]
      photo['$t']
    end
  end


  def self.get_sex(pet)
    sex = pet['sex']['$t'].downcase.to_sym
    SEXES.fetch(sex) { 'gender-unspecified '} # Fetch a sex, or list as gender-unspecified
  end


  def self.fetch_pet
    uri = URI(URL)
    uri.query = URI.encode_www_form(PARAMS)
    json = JSON.parse(Net::HTTP.get_response(uri).body)

    #PP.pp(json)  # Pretty-prints the response in the Terminal

    pet_json  = json['petfinder']['pet']

    Pet.new({
      breeds: get_breeds(pet_json),
      pic:   get_photo(pet_json),

      link:  "https://www.petfinder.com/petdetail/" + pet_json['id']['$t'],
      name:  pet_json['name']['$t'],
      id:    pet_json['id']['$t'],
      sex:   get_sex(pet_json),
      type:  pet_json['animal']['$t']
    })
  end
end
