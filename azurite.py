# === IMPORTS ===
import discord
from discord.ext import commands
import random
import json
import os
import sys
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from difflib import get_close_matches
import base64
import hashlib

# === LOGGING CONFIGURATION ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# === SECURITY ===
def _get_admin_id() -> int:
    """Get admin UID"""
    encrypted = "QXp1cml0ZV8xMzE2NjAwNTU3MzgwODI5MTg0X0FkbWlu"  # Azurite_1316600557380829184_Admin
    checksum = "69b622e60f012b698d6155874c013e9633cb2afa28497c0043a855109d3b12d2"  # SHA-256 of "1316600557380829184"
    
    try:
        # Decrypt the admin ID
        decoded = base64.b64decode(encrypted).decode('utf-8')
        logger.info(f"Decoded string: {decoded}")  # Log the decoded string for debugging
        
        parts = decoded.split('_')
        if len(parts) != 3:
            logger.error(f"Admin ID format verification failed: expected 3 parts, got {len(parts)}")
            return 0
            
        if parts[0] != "Azurite":
            logger.error(f"Admin ID format verification failed: expected 'Azurite', got '{parts[0]}'")
            return 0
            
        if parts[2] != "Admin":
            logger.error(f"Admin ID format verification failed: expected 'Admin', got '{parts[2]}'")
            return 0
        
        # Verify the checksum
        verify = hashlib.sha256(str(parts[1]).encode()).hexdigest()
        if verify != checksum:
            logger.error(f"Admin ID checksum verification failed: expected {checksum}, got {verify}")
            return 0
            
        admin_id = int(parts[1])
        logger.info(f"Admin ID verified successfully: {admin_id}")
        return admin_id
    except Exception as e:
        logger.error(f"Error verifying admin ID: {str(e)}")
        return 0

# === BOT CONFIGURATION ===
class Config:
    def __init__(self):
        # Get admin ID through secure method
        self.ADMIN_USER_ID = _get_admin_id()
        if self.ADMIN_USER_ID == 0:
            logger.critical("Failed to verify admin ID. Bot cannot start.")
            sys.exit(1)
        
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
                self.TOKEN = config['token']
                self.CHANNEL_ID = config['channel_id']
                self.TARGET_CHANNEL_ID = config['target_channel_id']
                self.TARGET_USER_ID = config['target_user_id']
                self.CURRENCY_NAME = config.get('currency_name', 'money')
        except FileNotFoundError:
            logger.error("config.json not found. Please create it with your bot configuration.")
            sys.exit(1)
        except KeyError as e:
            logger.error(f"Missing required configuration: {e}")
            sys.exit(1)
        except json.JSONDecodeError:
            logger.error("config.json is not valid JSON. Please check the format.")
            sys.exit(1)
        
        # Non-sensitive configuration
        self.BACKUP_INTERVAL = 3600  # 1 hour in seconds
        self.RNG_COOLDOWN = 30  # 30 seconds
        self.DATA_FILE = 'user_items.json'
        self.BACKUP_DIR = 'backups'

    def save_config(self):
        """Save the current configuration to config.json"""
        try:
            config_data = {
                'token': self.TOKEN,
                'channel_id': self.CHANNEL_ID,
                'target_channel_id': self.TARGET_CHANNEL_ID,
                'target_user_id': self.TARGET_USER_ID,
                'currency_name': self.CURRENCY_NAME
            }
            with open('config.json', 'w') as f:
                json.dump(config_data, f, indent=4)
            return True
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            return False

# Initialize configuration
config = Config()

# === BOT INITIALIZATION ===
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.guild_messages = True

bot = commands.Bot(command_prefix='.', intents=intents)

# === ITEM DEFINITIONS ===
item_descriptions = {
    1: "Oolong Tea: An oxidized Chinese tea. Different flavors and fragrances can be bought out depending on the degree of oxidation.",
    2: "Boba Tea: A popular drink with a bunch of tapioca balls at the bottom. The chewy tapioca balls are made from the root of the cassava plant.",
    3: "Ginger Tea: Hot water with grated ginger in it. It warms the body and prevents colds. It tastes delicious with honey mixed in.",
    4: "Cleopatra's Pearl Cocktail: A drink based on the story of Cleopatra dissolving one of her pearl earrings in a cup of vinegar. Said to be good for beauty.",
    5: "Non-Alcoholic Drink of Immortality: A non-alcoholic drink based on a legendary alcoholic beverage said to make the drinker immortal. It neither grants immortality, nor does it taste good.",
    6: "Ketchup: An exclusive writing instrument for a maid to use to write messages on omelettes. Considered a normal condiment by some people.",
    7: "Sugar: A basic seasoning that's primarily made up of sucrose. Be careful not to consume too much of it.",
    8: "Olive Oil: A vegetable oil created from olives. If you wielded it correctly, it will make you look cool as you cook.",
    9: "Astro Cake: A freeze-dried slice of cake sold to the public as space food. It's both healthy and vegetarian-friendly.",
    10: "Bubble Gum Bomb: A gum that makes an explosive sound when it's fully blown and popped. Weak-hearted people should not chew it.",
    11: "Maple Fudge: A British candy that's made by boiling down sugar, condensed milk, and butter, and then adding maple syrup. It's really sweet.",
    12: "Greek Yogurt: A food that's made by straining water from plain yogurt. The thick taste is popular and used in several dishes.",
    13: "Bunny Apples: Apples cut into bunny shapes. Often used as bait for certain animals and insects.",
    14: "Rock Hard Ice Cream: A cup of ice cream engineered to never melt. It can be carried around for a long time, even in summer. But it's so hard, ordinary spoons can't penetrate it.",
    15: "Sukiyaki Caramel: Sukiyaki-flavored caramels that combine the flavors of meat, soy sauce, eggs, and caramel. The flavors are all really strong and don't mix well.",
    16: "Candy Cigarette: A sweet cigarette-shaped candy. It's popular among kids who want to imitate adults.",
    17: "Gyoza In the Shape of a Face: A dumpling that's modeled after someone you swear you've seen somewhere before. The skin is thick and it's a little tough.",
    18: "Silver Earring: A simple earring that can look good on anyone. It's casually stylish.",
    19: "Crystal Bangle: A bangle made out of common crystal glass. It's sparkly and draws quite a bit of attention.",
    20: "Striped Necktie: A stylish tie both men and women can wear. It's convenient to have one around for special occasions.",
    21: "Bondage Boots: Enamel boots fit for a queen. They have high heels and long laces decorated with a chain. Made to be worn as shoes, but usable as art or an umbrella holder.",
    22: "Ultimate Academy Bracelet: A handcuff bracelet with the crest for the Ultimate Academy emblazoned on it. It is a symbol of friendship, even in the face of death and despair.",
    23: "Workout Clothes: Easy-to-move workout clothes that wick away any sweat. With these, you can work out all day and still be comfortable.",
    24: "Mono-Jinbei: Popular Japanese summer clothes colored black and white, like Monokuma. It's easy to move around in, and breathes well.",
    25: "Autumn-Colored Scarf: A chic autumn-colored scarf that can be used by men, women, and robots. It is very trendy and a fashionable accent to any outfit.",
    26: "Hand-Knit Sweater: A sweater that's been knitted with love in every stitch. Those who wear it can feel themselves enveloped in the power of love and will stay warm through even the coldest winter.",
    27: "Cheer Coat Uniform: A long coat with passionate red lining. It protects you from the cold and makes you burn with passion.",
    28: "Nail Brush: A brush for painting nails beautifully. With this, anyone can make their nails sparkle like magic. You can give it away, but something good might happen if you keep it.",
    29: "Wearable Blanket: A blanket that will completely defend you from the cold by closing off any gaps around your hands, neck, and feet. Moving around in it is near impossible.",
    30: "Beret: A size-adjustable beret. It's a pretty popular hat that lets you look trendy and somewhat artistic.",
    31: "Ladybug Brooch: A cute and fashionable brooch that resembles a seven-spotted ladybug. Despite how realistic it looks, it is not alive.",
    32: "Cufflinks: An accessory that is attached to the cuffs of a shirt. The black onyx design makes it look good on both men and women.",
    33: "Dog Tag: A dog tag used to identify soldiers. The same profile is engraved on two plates so that if the owner is killed, one is collected to report death.",
    34: "White Robot Mustache: A gentlemanly mustache that can be stuck on robots. Does not include antenna functions or earthquake powers.",
    35: "Book of the Blackened: A book of criminal offenses that contains records of the cruelest, most atrocious murders committed by humans. Many of these cases weren't released to the public.",
    36: "Feelings of Ham: How to raise hamsters...is not what this book is about. It's a book about raising domestic animals for meat. For those who are interested in the farming industry.",
    37: "Travel Journal: A thick journal packed with records of trips. However, it was actually written using vague knowledge and the rich imagination of someone looking at a world map.",
    38: "Dreams Come True ☆ Spell Book: A book that contains old magic gathered from all over the country and collected into an easy to read volume for kids. Any dangers have been removed, so only love spells are left.",
    39: "Story of Tokono: A collection of stories about the customs, legends, and knowledge of civilizations from long ago. It has a high scientific value.",
    40: "Spla-Teen Vogue: A teen magazine featuring many models just enjoying their summer. This magazine is meant for kids, not squids.",
    41: "Fun Book of Animals: An animal picture book for preschool kids. For some reason, bears are not featured in it.",
    42: "Latest Machine Parts Catalogue: A comprehensive catalog that features the latest cables, screws, motors, etc. It could be considered a fashion magazine for robots.",
    43: "Stainless Tray: A circular silver tray that shines like a mirror. It is befitting of a maid.",
    44: "Tennis Ball Set: A standard tennis ball four-pack set. Not only is it used for tennis, but it's also used for massage and weight loss exercises.",
    45: "High-End Headphones: Top-grade, high-end headphones. Use these if you truly want to hear the nuances in classical and jazz music.",
    46: "Teddy Bear: A typical stuffed toy bear that's not black and white. If you love it enough, then it might come to life one day.",
    47: "Milk Puzzle: A plain puzzle with one side as white as milk. It's said to be good for concentration training and is used for astronaut selection exams.",
    48: "Illusion Rod: A miracle rod that can show a happy illusion when it's spun in circles in front of someone's eyes.",
    49: "Hand Mirror: A pocket-sized mirror that is incredibly useful for checking your appearance.",
    50: "Prop Carrying Case: A case in high demand by cosplayers for its usability. Not only is it useful for conventions, but it's great for trips too.",
    51: "Japanese Doll Wig: A glamorous black wig that has hair like that of a Japanese doll. Even if you cut it, it grows back instantly.",
    52: "Photoshop Software: A photo editing software that lets you retouch photos. Turn a plain, freckled face into something flashy!",
    53: "Sewing Kit: A basic sewing kit that has a needle and several colors of thread. With this, you will always be prepared in case a button comes off.",
    54: "Flame Thunder: A broom that lets mages fly at high speeds when they sit on it. It's a little bent, but it can also be used as a fishing rod.",
    55: "Tattered Music Score: A tattered handwritten music score. Rumor has it that it's unpublished music from a certain famous composer.",
    56: "Indigo Hakama: Traditional Japanese clothing. This particular kind is made of high-quality cotton and used for martial arts. Wear it when it's time to spar.",
    57: "Fashionable Glasses: A fashionable accessory that appears to be a pair of glasses, but does not actually correct its wearer's vision.",
    58: "Gold Origami: An origami pack that has 24 sheets of gold origami paper. With this, you can create gorgeous origami.",
    59: "Plastic Moon Buggy Model: A plastic model of an actual buggy used by astronauts on the moon. It looks plain, but it's actually filled with a burning passion.",
    60: "I'm a Picture Book Artist!: An electronic device that's equipped with an AI to produce a new picture book every time it's turned on. Great for kids who love hearing bed-time stories.",
    61: "Hand Grips: A device for grip training. The strength of a punch is determined by grip strength, weight, and speed combined.",
    62: "Commemorative Medal Set: A medal set Monokuma made of himself and the Monokubs. You can feel the care he put into making it. You can give it away, but something good might happen if you keep it.",
    63: "Metronome: A musical device that is used to match the tempo when playing an instrument. A basic pendulum type.",
    64: "Sketchbook: An art book for sketches. It's pocket-sized so it's convenient to carry around.",
    65: "Art Manikin: A model doll that has the same joints as humans. It's pretty versatile and can stay balanced in positions humans can't maintain.",
    66: "Bird Food: A carefully selected collection of fresh seeds for domestic pigeons. Wild pigeons can't appreciate the increased quality, so it would be a waste to give them these.",
    67: "Proxilingual Device: A tool that can translate any language, even animal sounds. It can pick up a dog's bark and eloquently describe the emotions in it with an electronic bark.",
    68: "Gourd Insect Trap: An opaque, gourd-shaped insect keeper. Used for keeping bugs to listen to the noises they make.",
    69: "Potted Banyan Tree: A potted banyan tree with spirits living inside it. It is said to be good luck. It grows aerial roots from the middle of its trunk.",
    70: "Pocket Tissue: A normal package of tissues. It's best to carry it alongside a handkerchief.",
    71: "Dancing Haniwa: A ceramic figure from the Japanese Kofun period. It is said to resemble a person dancing very intensely.",
    72: "Work Chair Of Doom: The ultimate work station with a comfy chair and so much technology that you will never want to get up. Those who sit here will be in danger of becoming obese.",
    73: "3-Hit KO Sandbag: Regardless of whether it's hit by a kick from a sickly child or a punch from a superhuman adult, this punching bag will always break on the third hit.",
    74: "Sports Towel: A towel that's perfect for hanging around your neck to wipe off sweat. It's the color of the bright, blue sky on a youthful summer day.",
    75: "Steel Glasses Case: A sturdy glasses case that won't break, even if it's stomped on by an Exisal. No matter what abuse it takes, the glasses inside will be kept safe.",
    76: "Robot Oil: An oil that's necessary to have when making robots. It has started to separate, so the top half is diluted. Please be sure to shake before use.",
    77: "Clock-Shaped Gaming Console: A pocket watch-shaped game console with monochrome LCD and several buttons. Play a game called 'Factory' and mash buttons to create more bears!",
    78: "Everywhere Parasol: A parasol with a stand so it can be used anywhere. Set it up poolside to feel fancy! You can give it away, but something good might happen if you keep it.",
    79: "Three-Layered Lunch Box: A family-sized lunch box that can fit a variety of side dishes. Perfect for a picnic.",
    80: "Aluminum Water Bottle: A round, retro water bottle. Having it slung over your shoulder makes you want to go on an adventure.",
    81: "Jelly Balls: Squishy, colorful beads that swell to marble size when wet. Good for decoration and gardening. Lining up 4 of the same color won't make them vanish.",
    82: "Upbeat Humidifier: It humidifies your room based on the amount of tears you have shed. Great for gloomy people, but to cheerful people, it's just a paperweight.",
    83: "Earnest Compass: A compass that ignores the North Pole and South Pole, and instead points to the owner's loved ones. A must-have for stalkers.",
    84: "Semazen Doll: A ceramic doll that spins like a Whirling Dervish. It's a very popular Turkish souvenir.",
    85: "Weathercock of Barcelous: A weathercock that imitates the Portuguese 'Rooster of Barcelos,' a symbol of the truth, this is a popular souvenir from Portugal.",
    86: "Pillow of Admiration: A pillow that helps you sleep well and gives you wonderful dreams. However, the dreams will show an entire lifetime making you feel intensely empty after you wake up.",
    87: "46 Moves of the Killing Game: A card game with Japanese characters relating to killing games. Some cards are, 'A metal bat to kill demons,' 'Blackened are soaked in blood,' and 'Certain evidence over arguments.'",
    88: "The Monkey's Paw: The mummified hand of a monkey said to grant three wishes. However, none of the wishes it grants have happy endings.",
    89: "Art Piece of Spring: An ornament that looks like a urinal. The more you look at it, the more you start to question what art *really* is.",
    90: "Electric Tempest: A cool high-powered water gun. The water shoots over 10 yards and it can be fired continuously for a whole minute. Fun for kids and adults!",
    91: "Space Egg: Object made out of borosilicate glass. Depending on the angle, it changes form. The mysterious pattern is what makes it popular.",
    92: "Death Flag: The blackened might be one of us, so I refuse to stay with you guys! I'm gonna go hide in my room!",
    93: "Survival Flag: The chance of this succeeding is only 5%. No one has ever made it out alive before...but this is my last chance to survive.",
    94: "Helping Yacchi: A robot mascot that looks like a killer whale. It can sense when its owner is distressed, and offers a research solution.",
    95: "Home Planet: A mini planetarium machine that can project the cosmos onto your bedroom walls when it's time for bed. Comes with a narration by a popular voice actor.",
    96: "Super Lucky Button: A shiny button that makes its owner feel like their luck will turn around. It may or may not pull in a powerful wave of luck.",
    97: "Sparkly Sheet: A cleaning sheet that gets rid of any mess in the kitchen sink or dirt on the faucet. Can also be used to clean robots.",
    98: "Hammock: Bedding created by hanging a net between two poles or trees. Lounging in one of these is something everyone has dreamed of at least once.",
    99: "Cleansing Air Freshener: A spray air freshener. It has holy water mixed in, and is said to repel ghosts and paranormal entities.",
    100: "Flower for Floromancy: 'Loves me, loves me not, loves me...' An artificial flower used for flower fortune-telling. It has an odd number of petals to soothe the pain of unrequited love.",
    101: "Marigold Seeds: Marigold seeds that bloom into colorful flowers. By way, marigolds symbolize 'despair.'",
    102: "Rock-Paper-Scissors Cards: A set of cards containing four rocks, four papers, and four scissors. If you bet your life on this game, it can be a thrilling psychological battle.",
    103: "Perfect Laser Gun: A replica of a laser gun used by upstanding citizens to punish rebellious or unhappy people. When carrying it around, be sure to watch your coefficient.",
    104: "Someone's Student ID: A replica of a student ID from some academy. There are many different designs of ID as there are talented students.",
    105: "Bear Ears: A headband with Monokuma ears. When worn, it picks up your brainwaves and the ears wiggle according to your emotions.",
    106: "Dangan Werewolf: A party game of hope and despair. Draw cards and become the characters to start deducing and debating! Now on sale!",
    107: "Tentacle Machine: An extremely handy reacher grabber. Once you use it, you can't live without it.",
    108: "Rice Toy Blocks: Toy blocks made out of rice, so they're safe for babies to put in their mouths. But they'll go bad if they aren't eaten right away.",
    109: "Cosmic Blanket: Aluminum film that makes excellent insulation. It warms your body when you wrap it around yourself, making it handy for outdoor activities.",
    110: "Fully-Automated Shaved Ice Machine: A shaved ice machine that automatically crushes up ice and pours strawberry syrup on top.",
    111: "Gun of Man's Passion: A model of an imaginary weapon. It's powerful, but only the worthy may fire it. Embrace it to feel a man's fantasy. You can give it away, but something good might happen if you keep it.",
    112: "Pure-White Practice Sword: An ornamental katana that contains a divine power capable of taking out ordinary people with a single slash. You can give it away, but something good might happen if you keep it!",
    113: "Dark Belt: A black-ish belt worn with karate clothes. It can only be worn by those with justice in their hearts. You can give it away, but something good might happen if you keep it.",
    8046: "✦ Developer's Toolkit ✧: A special toolkit containing various development tools and utilities. This item is exclusive to the developer and cannot be obtained through normal means. TWL and AZR were here.. probably.",
    8047: "The Azureblade : A almost-mythical scythe made by Rumi Fujiki. The scythe contains a powerful PC built in, and AI fighting abilities. This item is exclusive to Rumi and cannot be obtained through normal means."
}

# === ITEM CATEGORIZATION ===
item_categories = {
    'drinks': {'items': list(range(1, 6)) + [80], 'emoji': '🥤'},
    'food': {'items': list(range(6, 18)) + [66, 79, 81, 108], 'emoji': '🍽️'},
    'accessories': {'items': [18, 19, 20, 21, 22, 31, 32, 33, 34, 49, 51, 57, 62, 75, 78, 96, 104, 105], 'emoji': '💍'},
    'books': {'items': list(range(35, 43)) + [55, 64, 87, 106], 'emoji': '📚'},
    'tools': {'items': [52, 53, 54, 61, 67, 68, 76, 82, 83, 90, 95, 97, 99, 103, 107, 110, 111, 112, 8046, 8047], 'emoji': '🛠️'},
    'clothing': {'items': [23, 24, 25, 26, 27, 29, 30, 56, 74, 109, 113], 'emoji': '👕'},
    'misc': {'items': [69, 70, 71, 72, 73, 77, 84, 85, 86, 88, 89, 91, 92, 93, 94, 98, 100, 101, 102], 'emoji': '📦'}
}

# === CATEGORY ALIASES ===
category_aliases = {
    'drink': 'drinks',
    'beverage': 'drinks',
    'beverages': 'drinks',
    'foods': 'food',
    'meal': 'food',
    'meals': 'food',
    'accessory': 'accessories',
    'acc': 'accessories',
    'book': 'books',
    'reading': 'books',
    'tool': 'tools',
    'utility': 'tools',
    'cloth': 'clothing',
    'clothes': 'clothing',
    'wear': 'clothing',
    'miscellaneous': 'misc',
    'other': 'misc'
}

# === INVENTORY MANAGEMENT ===
class ItemManager:
    def __init__(self):
        self.data_file = config.DATA_FILE
        self.backup_dir = config.BACKUP_DIR
        self.user_items = self.load_user_items()
        self._setup_backup_system()

    def _setup_backup_system(self):
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)

    def load_user_items(self) -> Dict:
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error loading user items: {e}")
            return {}

    def save_user_items(self, data: Dict):
        try:
            # First save to a temporary file
            temp_file = self.data_file + '.tmp'
            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=4)

            # Then rename it to the actual file (atomic operation)
            os.replace(temp_file, self.data_file)
            
        except IOError as e:
            logger.error(f"IO Error saving user items: {e}")
            raise
        except Exception as e:
            logger.error(f"Error saving user items: {e}")
            raise

    def create_backup(self):
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = os.path.join(self.backup_dir, f'backup_{timestamp}.json')
            with open(backup_file, 'w') as f:
                json.dump(self.user_items, f, indent=4)
            logger.info(f"Backup created: {backup_file}")
        except Exception as e:
            logger.error(f"Error creating backup: {e}")

    def add_item(self, user_id: int, item_id: int) -> bool:
        try:
            # Validate inputs
            if not isinstance(user_id, int) or not isinstance(item_id, int):
                logger.error(f"Invalid input types: user_id={type(user_id)}, item_id={type(item_id)}")
                return False

            user_id_str = str(user_id)
            
            # Initialize user's inventory if it doesn't exist
            if user_id_str not in self.user_items:
                self.user_items[user_id_str] = []
            
            # Add the item
            self.user_items[user_id_str].append(item_id)
            
            # Try to save
            try:
                self.save_user_items(self.user_items)
            except IOError as e:
                logger.error(f"Failed to save user items (IO Error): {e}")
                # Remove the item if we couldn't save
                self.user_items[user_id_str].remove(item_id)
                return False
            except Exception as e:
                logger.error(f"Failed to save user items (Unknown Error): {e}")
                # Remove the item if we couldn't save
                self.user_items[user_id_str].remove(item_id)
                return False
                
            return True
            
        except ValueError as e:
            logger.error(f"Value error adding item: {e}")
            return False
        except TypeError as e:
            logger.error(f"Type error adding item: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error adding item: {e}")
            return False

    def remove_item(self, user_id: int, item_id: int) -> bool:
        try:
            user_id_str = str(user_id)
            if user_id_str in self.user_items and item_id in self.user_items[user_id_str]:
                self.user_items[user_id_str].remove(item_id)
                self.save_user_items(self.user_items)
                return True
            return False
        except Exception as e:
            logger.error(f"Error removing item: {e}")
            return False

    def get_user_items(self, user_id: int) -> List[int]:
        return self.user_items.get(str(user_id), [])

    def clear_user_items(self, user_id: int) -> bool:
        try:
            user_id_str = str(user_id)
            if user_id_str in self.user_items:
                # If this is the admin user, preserve special items
                if user_id == config.ADMIN_USER_ID:
                    self.user_items[user_id_str] = [8046, 8047]  # Special items
                else:
                    self.user_items[user_id_str] = []
                self.save_user_items(self.user_items)
            return True
        except Exception as e:
            logger.error(f"Error clearing user items: {e}")
            return False

# Initialize item manager
item_manager = ItemManager()

# === COMMAND IMPLEMENTATIONS ===
@bot.event
async def on_ready():
    logger.info(f'✅ Bot is online: {bot.user}')
    bot.loop.create_task(backup_task())
    
    # Ensure admin has special items
    admin_items = item_manager.get_user_items(config.ADMIN_USER_ID)
    if 8046 not in admin_items:  # Developer's Toolkit
        item_manager.add_item(config.ADMIN_USER_ID, 8046)
        logger.info("Added Developer's Toolkit to admin user")
    if 8047 not in admin_items:  # The Azureblade
        item_manager.add_item(config.ADMIN_USER_ID, 8047)
        logger.info("Added The Azureblade to admin user")

async def backup_task():
    while True:
        await asyncio.sleep(config.BACKUP_INTERVAL)
        item_manager.create_backup()

@bot.command(name='rng', aliases=['roll', 'gacha'])
@commands.cooldown(1, config.RNG_COOLDOWN, commands.BucketType.user)
async def rng(ctx):
    if ctx.channel.id != config.CHANNEL_ID:
        await ctx.send("❌ This command only works in the designated channel.")
        return

    try:
        roll = random.randint(1, 113)  # Changed from 120 to 113 to exclude Dev Toolkit
        logger.info(f"RNG roll by {ctx.author}: {roll}")

        if roll <= 113:
            item_description = item_descriptions.get(roll, f"🎉 Success! You got item #{roll}!")
            embed = discord.Embed(
                title="🎲 Gacha Roll Result",
                description=f"✅ You got item #{roll}!",
                color=discord.Color.blue()
            )
            embed.add_field(name="Item Description", value=item_description, inline=False)
            
            if item_manager.add_item(ctx.author.id, roll):
                await ctx.send(embed=embed)
                
                target_channel = await bot.fetch_channel(config.TARGET_CHANNEL_ID)
                if target_channel:
                    await target_channel.send(f"<@{config.TARGET_USER_ID}> Please remove 15 {config.CURRENCY_NAME} from {ctx.author.mention}.")
            else:
                await ctx.send("❌ Failed to add item to your inventory. Please try again.")
        else:
            await ctx.send("❌ The machine got stuck... Try again another time!")

    except Exception as e:
        logger.error(f"Error in rng command: {e}")
        await ctx.send("❌ An error occurred. Please try again later.")

@rng.error
async def rng_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        minutes = int(error.retry_after / 60)
        seconds = int(error.retry_after % 60)
        await ctx.send(f"⏰ Please wait {minutes}m {seconds}s before using this command again.")

@bot.command(name='inventory', aliases=['inv', 'items'])
async def inventory(ctx, target_user: Optional[discord.Member] = None, *, args: str = ""):
    # If no user is specified, use the command author
    user = target_user or ctx.author
    
    # Don't allow checking bot inventories
    if user.bot:
        await ctx.send("❌ Bots don't have inventories!")
        return

    items = item_manager.get_user_items(user.id)
    
    if not items:
        if user == ctx.author:
            await ctx.send("You don't have any items yet!")
        else:
            await ctx.send(f"{user.name} doesn't have any items yet!")
        return

    # Parse arguments for sorting
    sort_by = "category"  # default sorting
    if "--sort" in args or "-s" in args:
        # Split on the first occurrence of the flag
        if "--sort" in args:
            parts = args.split("--sort", 1)
        else:
            parts = args.split("-s", 1)
            
        if len(parts) > 1:
            sort_arg = parts[1].strip().lower()
            # Take the first word after the flag
            sort_arg = sort_arg.split()[0] if sort_arg.split() else ""
            if sort_arg in ["id", "name", "category"]:
                sort_by = sort_arg

    embed = discord.Embed(
        title=f"🎒 {user.name}'s Inventory",
        description=f"Sorting by: {sort_by}",
        color=discord.Color.green()
    )

    # Count total unique items and total items
    unique_items = len(set(items))
    total_items = len(items)
    embed.set_footer(text=f"Unique items: {unique_items} | Total items: {total_items}")

    # Count occurrences of each item
    item_counts = {}
    for item in items:
        item_counts[item] = item_counts.get(item, 0) + 1

    if sort_by == "id":
        # Sort by ID
        sorted_items = sorted(set(items))
    
    elif sort_by == "name":
        # Sort by item name/description
        sorted_items = sorted(set(items), 
                            key=lambda x: item_descriptions.get(x, '').split(':', 1)[0] if ':' in item_descriptions.get(x, '') 
                            else item_descriptions.get(x, ''))
    
    elif sort_by == "category":
        # Group items by category
        for category, info in item_categories.items():
            user_category_items = [i for i in items if i in info['items']]
            if user_category_items:
                # Create item list with counts
                item_list = []
                for item_id in sorted(set(user_category_items)):
                    count_str = f" (x{item_counts[item_id]})" if item_counts[item_id] > 1 else ""
                    item_list.append(f"#{item_id}{count_str} - {item_descriptions.get(item_id, f'Item {item_id}')}")
                
                embed.add_field(
                    name=f"{info['emoji']} {category.title()} ({len(user_category_items)} items)",
                    value='\n'.join(item_list),
                    inline=False
                )
        await ctx.send(embed=embed)
        return

    # For ID and name sorting, add fields after sorting
    for item_id in sorted_items:
        count_str = f" (x{item_counts[item_id]})" if item_counts[item_id] > 1 else ""
        # Find the category for the emoji
        item_category = next((cat for cat, info in item_categories.items() 
                            if item_id in info['items']), None)
        category_emoji = item_categories[item_category]['emoji'] if item_category else ""
        
        embed.add_field(
            name=f"{category_emoji} #{item_id}{count_str}",
            value=item_descriptions.get(item_id, f'Item {item_id}'),
            inline=False
        )

    await ctx.send(embed=embed)

@bot.command(name='categories', aliases=['cats', 'list'])
async def list_categories(ctx):
    embed = discord.Embed(
        title="📋 Item Categories",
        description="Here are all available item categories:",
        color=discord.Color.blue()
    )
    
    for category, info in item_categories.items():
        # Get all valid aliases for this category
        aliases = [k for k, v in category_aliases.items() if v == category]
        aliases_str = f"\nAliases: {', '.join(aliases)}" if aliases else ""
        
        # Count items in category
        item_count = len(info['items'])
        
        embed.add_field(
            name=f"{info['emoji']} {category.title()} ({item_count} items)",
            value=f"Use `.search -c {category}` to view items{aliases_str}",
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command(name='random', aliases=['rand'])
async def random_item(ctx, *, args: str = ""):
    category = None
    
    # Parse category filter
    if '--category' in args or '-c' in args:
        parts = args.split('--category' if '--category' in args else '-c')
        if len(parts) > 1:
            category = parts[1].strip().lower()
    elif args:  # If there's an argument but no flag, treat it as category
        category = args.lower()

    if category:
        # Check aliases
        category = category_aliases.get(category, category)
        
        if category not in item_categories:
            categories_list = ", ".join(item_categories.keys())
            await ctx.send(f"❌ Invalid category. Available categories: {categories_list}")
            return
        
        items = item_categories[category]['items']
    else:
        items = list(item_descriptions.keys())
        if 8046 in items:
            items.remove(8046)
    
    item_id = random.choice(items)
    
    embed = discord.Embed(
        title="🎲 Random Item",
        description=f"Here's a random item{f' from {category}' if category else ''}:",
        color=discord.Color.gold()
    )
    
    # Find the category of the item
    item_category = next((cat for cat, info in item_categories.items() 
                         if item_id in info['items']), None)
    
    if item_category:
        category_emoji = item_categories[item_category]['emoji']
        embed.add_field(
            name=f"{category_emoji} Item #{item_id}",
            value=item_descriptions[item_id],
            inline=False
        )
    else:
        embed.add_field(
            name=f"Item #{item_id}",
            value=item_descriptions[item_id],
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command(name='search', aliases=['find'])
async def search_items(ctx, *, query: str = ""):
    # Parse query for filters
    category = None
    item_id = None
    original_query = query
    
    # Parse category filter
    if '--category' in query or '-c' in query:
        parts = query.split('--category' if '--category' in query else '-c')
        if len(parts) > 1:
            query = parts[0].strip()
            category = parts[1].strip().lower()
    
    # Parse ID filter
    is_id_search = '--id' in original_query or '-i' in original_query
    if is_id_search:
        parts = query.split('--id' if '--id' in query else '-i')
        if len(parts) > 1:
            query = parts[0].strip()
            try:
                item_id = int(parts[1].strip())
            except ValueError:
                await ctx.send("❌ Invalid item ID. Please provide a number.")
                return
    
    query = query.lower()
    matches = []
    
    # Get all item descriptions for fuzzy matching
    all_descriptions = {item_id: desc.lower() for item_id, desc in item_descriptions.items()}
    
    # Filter by ID if specified
    if item_id is not None:
        if item_id not in all_descriptions:
            await ctx.send(f"❌ Item ID {item_id} does not exist.")
            return
        searchable_items = {item_id: all_descriptions[item_id]}
    else:
        # Filter by category if specified
        if category:
            # Find the category
            category_found = False
            for cat_name, cat_info in item_categories.items():
                if category in cat_name:
                    category = cat_name
                    category_found = True
                    break
            
            if not category_found:
                await ctx.send(f"❌ Category '{category}' not found. Available categories: {', '.join(item_categories.keys())}")
                return

            # Only search within the specified category
            searchable_items = {
                item_id: desc for item_id, desc in all_descriptions.items() 
                if item_id in item_categories[category]['items']
            }
        else:
            searchable_items = all_descriptions
    
    # If ID search, just add the item
    if item_id is not None:
        matches.append((item_id, item_descriptions[item_id]))
    else:
        # First try exact matches
        for item_id, description in searchable_items.items():
            if query in description:
                matches.append((item_id, item_descriptions[item_id]))
        
        # If no exact matches and we have a query, try fuzzy matching
        if not matches and query:
            # Get all words from descriptions
            all_words = set()
            for desc in searchable_items.values():
                all_words.update(desc.split())
            
            # Find close matches to the query
            close_matches = get_close_matches(query, all_words, n=5, cutoff=0.6)
            
            # Search for items containing any of the close matches
            for item_id, description in searchable_items.items():
                if any(match in description for match in close_matches):
                    matches.append((item_id, item_descriptions[item_id]))
        # If no query, show all items in category or all items
        elif not query:
            matches.extend((item_id, item_descriptions[item_id]) for item_id in searchable_items.keys())
    
    if not matches:
        category_msg = f" in category '{category}'" if category else ""
        id_msg = f" with ID {item_id}" if is_id_search else ""
        query_msg = f" matching '{query}'" if query else ""
        await ctx.send(f"No items found{category_msg}{id_msg}{query_msg}. Try different keywords or check the spelling.")
        return

    # Build the description based on search type
    description_parts = [f"Found {len(matches)} items"]
    if category:
        description_parts.append(f"in {category}")
    if is_id_search:
        description_parts.append(f"with ID {item_id}")
    elif query:
        description_parts.append(f"matching '{query}'")

    embed = discord.Embed(
        title="🔍 Search Results",
        description=" ".join(description_parts),
        color=discord.Color.blue()
    )

    # Sort matches by relevance (exact matches first, then fuzzy matches)
    if not is_id_search and query:  # Only sort if not searching by ID and we have a query
        matches.sort(key=lambda x: query in x[1].lower(), reverse=True)

    for item_id, description in matches[:10]:  # Limit to 10 results
        # Highlight the matching part in the description
        highlighted_desc = description
        if query and query in description.lower():
            start_idx = description.lower().find(query)
            end_idx = start_idx + len(query)
            highlighted_desc = (
                description[:start_idx] + 
                f"**{description[start_idx:end_idx]}**" + 
                description[end_idx:]
            )
        
        embed.add_field(name=f"Item #{item_id}", value=highlighted_desc, inline=False)

    if len(matches) > 10:
        embed.set_footer(text=f"... and {len(matches) - 10} more items")

    await ctx.send(embed=embed)

@bot.command(name='give', aliases=['trade'])
async def give_item(ctx, recipient: discord.User, item_id: int):
    if recipient.bot:
        await ctx.send("❌ You cannot give items to bots!")
        return

    if item_id in [8046, 8047]:  # Special items
        await ctx.send("❌ Special items cannot be given to other users.")
        return

    sender_items = item_manager.get_user_items(ctx.author.id)
    if item_id not in sender_items:
        await ctx.send(f"❌ You do not have item #{item_id} to give.")
        return

    if item_manager.remove_item(ctx.author.id, item_id) and item_manager.add_item(recipient.id, item_id):
        embed = discord.Embed(
            title="🎁 Item Transfer",
            description=f"{ctx.author.mention} has given an item to {recipient.mention}",
            color=discord.Color.green()
        )
        embed.add_field(name=f"Item #{item_id}", value=item_descriptions.get(item_id, f"Item {item_id}"), inline=False)
        await ctx.send(embed=embed)
    else:
        await ctx.send("❌ Failed to transfer the item. Please try again.")

def has_admin_permission(ctx):
    return ctx.author.guild_permissions.manage_guild or ctx.author.id == config.ADMIN_USER_ID

@bot.command(name='admin')
async def admin(ctx, action: str = None, user: discord.User = None, item_id: Optional[int] = None):
    if not has_admin_permission(ctx):
        await ctx.send("❌ You don't have permission to use admin commands.")
        return

    # Block all attempts to modify special items
    if item_id in [8046, 8047]:  # Special items
        await ctx.send("❌ Special items cannot be modified through admin commands.")
        return

    if action is None:
        embed = discord.Embed(
            title="🔧 Admin Command Usage",
            description="Here's how to use the admin commands:",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Add Item",
            value="`.admin add @user item_id`\nExample: `.admin add @user 42`",
            inline=False
        )
        embed.add_field(
            name="Remove Item",
            value="`.admin remove @user item_id`\nExample: `.admin remove @user 42`",
            inline=False
        )
        embed.add_field(
            name="Clear Inventory",
            value="`.admin clear @user`\nExample: `.admin clear @user`",
            inline=False
        )
        await ctx.send(embed=embed)
        return

    if action not in ['add', 'remove', 'clear']:
        await ctx.send("❌ Invalid action. Use 'add', 'remove', or 'clear'.")
        return

    if user is None:
        await ctx.send("❌ Please mention a user. Example: `.admin add @user 42`")
        return

    if action in ['add', 'remove'] and item_id is None:
        await ctx.send(f"❌ Please specify an item ID. Example: `.admin {action} @user 42`")
        return

    try:
        if action == 'add' and item_id is not None:
            if item_manager.add_item(user.id, item_id):
                await ctx.send(f"✅ Added item #{item_id} to {user.mention}'s inventory.")
            else:
                await ctx.send("❌ Failed to add item.")
        elif action == 'remove' and item_id is not None:
            if item_manager.remove_item(user.id, item_id):
                await ctx.send(f"✅ Removed item #{item_id} from {user.mention}'s inventory.")
            else:
                await ctx.send(f"❌ {user.mention} doesn't have item #{item_id}.")
        elif action == 'clear':
            if item_manager.clear_user_items(user.id):
                await ctx.send(f"✅ Cleared {user.mention}'s inventory.")
            else:
                await ctx.send(f"❌ Failed to clear {user.mention}'s inventory.")
    except Exception as e:
        logger.error(f"Error in admin command: {e}")
        await ctx.send("❌ An error occurred while performing the admin action.")

@bot.command(name='guide', aliases=['commands', 'info'])
async def guide_command(ctx):
    embed = discord.Embed(
        title="🤖 Bot Guide",
        description="Here are all available commands and their options:",
        color=discord.Color.blue()
    )
    
    commands_info = {
        'rng': {
            'title': '🎲 Roll for Items',
            'value': '`.rng` (aliases: `roll`, `gacha`)\n'
                    '• Roll for a random item\n'
                    '• 30-second cooldown between uses'
        },
        'inventory': {
            'title': '🎒 Inventory Management',
            'value': '`.inventory [@user] [options]` (aliases: `inv`, `items`)\n'
                    '• View your inventory or another user\'s\n'
                    '• **Sorting options:**\n'
                    '  `.inventory --sort category` (default)\n'
                    '  `.inventory --sort id`\n'
                    '  `.inventory --sort name`\n'
                    '• Short flag: `-s` (e.g., `.inv -s id`)\n'
                    '• Examples:\n'
                    '  `.inv @Friend`\n'
                    '  `.inv @Friend -s name`'
        },
        'search': {
            'title': '🔍 Search Items',
            'value': '`.search [query]` (alias: `find`)\n'
                    '• Search items by description\n'
                    '• **Options:**\n'
                    '  `-c [category]` - Search in specific category\n'
                    '  `-i [id]` - Search by item ID\n'
                    '• Examples:\n'
                    '  `.search sword`\n'
                    '  `.search -c tools`\n'
                    '  `.search -i 42`'
        },
        'random': {
            'title': '🎯 Random Item',
            'value': '`.random [category]` (alias: `rand`)\n'
                    '• Get a random item\n'
                    '• **Options:**\n'
                    '  `-c [category]` - Random item from category\n'
                    '• Examples:\n'
                    '  `.random`\n'
                    '  `.random tools`\n'
                    '  `.random -c food`'
        },
        'categories': {
            'title': '📋 View Categories',
            'value': '`.categories` (aliases: `cats`, `list`)\n'
                    '• List all item categories\n'
                    '• Shows category aliases\n'
                    '• Shows item count per category'
        },
        'give': {
            'title': '🎁 Give Items',
            'value': '`.give @user item_id` (alias: `trade`)\n'
                    '• Give an item to another user\n'
                    '• Example: `.give @Friend 42`'
        },
        'admin': {
            'title': '⚙️ Admin Commands',
            'value': '`.admin [action] @user [item_id]`\n'
                    '• Requires manage server permission\n'
                    '• **Actions:**\n'
                    '  `add` - Add item to user\n'
                    '  `remove` - Remove item from user\n'
                    '  `clear` - Clear user\'s inventory\n'
                    '• Use `.admin` for detailed help'
        }
    }
    
    for cmd_info in commands_info.values():
        embed.add_field(
            name=cmd_info['title'],
            value=cmd_info['value'],
            inline=False
        )
    
    embed.set_footer(text="Use the commands without [] brackets • Replace text in [] with your input")
    
    await ctx.send(embed=embed)

@bot.command(name='setcurrency', aliases=['currency'])
async def set_currency(ctx, *, currency_name: str = None):
    """Set or view the currency name used for the gacha system"""
    if not has_admin_permission(ctx):
        await ctx.send("❌ You don't have permission to use this command.")
        return
        
    if currency_name is None:
        # Just display the current currency name
        embed = discord.Embed(
            title="💰 Currency Settings",
            description=f"Current currency name: **{config.CURRENCY_NAME}**",
            color=discord.Color.gold()
        )
        embed.add_field(
            name="How to change",
            value="Use `.setcurrency [new name]` to change the currency name.\nExample: `.setcurrency coins`",
            inline=False
        )
        await ctx.send(embed=embed)
        return
        
    # Update the currency name
    config.CURRENCY_NAME = currency_name
    if config.save_config():
        embed = discord.Embed(
            title="💰 Currency Updated",
            description=f"Currency name has been changed to: **{currency_name}**",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    else:
        await ctx.send("❌ Failed to save the currency name. Please check the logs for details.")

# === BOT EXECUTION ===
if __name__ == "__main__":
    try:
        bot.run(config.TOKEN)
    except Exception as e:
        logger.critical(f"Failed to start bot: {e}")