require 'minitest/autorun'
require_relative '../lib/cuties/pet'

describe Pet, 'Pet' do

  before do
    @pet = Pet.new({
      id:    'id',
      breeds: 'breeds',
      desc:  'desc',
      link:  'link',
      name:  'name',
      pic:   'pic',
      sex:   'sex',
      type:  'type'
    })
  end

  describe "#breed_or_animal" do

    describe "when type is a Small & Furry" do
      let(:pet) { Pet.new(type: 'Small & Furry', breeds: ['breed']) }

      it "returns the breed" do
        pet.breed_or_animal.must_equal '#Breed'
      end
    end

    describe "when type is a Pig" do
      let(:pet) { Pet.new(type: 'Pig', breeds: ['breed', 'other']) }

      it "returns the breed + 'pig'" do
        pet.breed_or_animal.must_equal '#Breed / #Other mix #Pig'
      end
    end

    describe "when type is a Rabbit" do
      let(:pet) { Pet.new(type: 'Rabbit', breeds: ['breed']) }

      it "returns the breed + 'rabbit'" do
        pet.breed_or_animal.must_equal '#Breed #Rabbit'
      end
    end
  end

end
