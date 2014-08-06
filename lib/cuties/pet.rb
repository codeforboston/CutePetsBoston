class Pet
  
  attr_reader :id,
              :link,
              :name,
              :sex,
              :breed,
              :type,
              :desc,
              :pic

  def initialize(attributes)
    @id    = attributes[:id]
    @breed = attributes[:breed]
    @desc  = attributes[:desc]
    @link  = attributes[:link]
    @name  = attributes[:name]
    @pic   = attributes[:pic]
    @sex   = attributes[:sex]
    @type  = attributes[:type]
  end

  def breed_or_animal
    # If it's a rabbit or pig, mention that it's a rabbit or pig.
    # Otherwise, just list the breed.
    # 'Small & Furry' animals like mice & chinchillas
    # have their species in 'breed'

    return "#{breed} #{type.downcase}" if ['#Rabbit', '#Pig'].include? type
    return breed.downcase if type == '#Small&Furry'
    breed
  end

  def message
    "#{name}, a #{sex} #{breed_or_animal}. #{link}"
  end

  def error?
    # attributes['code']
  end
end
