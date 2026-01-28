class Pet

  attr_reader :id,
              :link,
              :name,
              :sex,
              :breeds,
              :type,
              :desc,
              :pic

  @@replace = {"#DomesticShortHair" => "#ShortHair",
              "#DomesticLongHair" => "#LongHair"}

  def initialize(attributes)
    @id     = attributes[:id]
    @breeds = attributes[:breeds]
    @desc   = attributes[:desc]
    @link   = attributes[:link]
    @name   = attributes[:name]
    @pic    = attributes[:pic]
    @sex    = attributes[:sex]
    @type   = attributes[:type]
  end

  def breed_or_animal
    # If it's a rabbit, pig or cat, mention that it's a rabbit, pig, or cat.
    # Otherwise, just list the breed.
    # 'Small & Furry' animals like mice & chinchillas
    # have their species in 'breed'

    return "#{format_breed} #{hashtagify(type)}" if ['Rabbit', 'Pig', 'Cat'].include? type
    return "#{format_breed}" if type == 'Small & Furry'
    return format_breed
  end

  def hashtagify(words)
    # given a 'word' return #Word
    # given a 'string of words' return #StringOfWords

    split = words.split(' ')
    return '#' + split.map{ |b| b.capitalize() }.join('')
  end

  def format_breed
    breed_string = breeds.map{ |b| hashtagify(b) }.join(' / ')
    breed_string << ' mix' if breed_string.include?('/')

    if @@replace.include? breed_string
      return @@replace[breed_string]
    end

    breed_string
  end

  def message
    "#{name.my_titleize}, a #{sex} #{breed_or_animal}. #{link}"
  end

  def error?
    # attributes['code']
  end
end
