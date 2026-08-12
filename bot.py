import asyncio
import random
import string
import logging
import os
import aiohttp
from aiohttp import web
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters, ConversationHandler,
)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))
PORT = int(os.environ.get("PORT", "10000"))

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not set")

SEARCH_TIMEOUT = 45
CHECK_DELAY = 0.05
MAX_RESULTS = 5
BATCH_SIZE = 20
CONCURRENT_LIMIT = 15
WORD_INPUT = 1

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

TAKEN_5 = {
    "apple","hello","world","admin","users","tests","music","video","photo",
    "games","sport","money","trade","crypt","block","chain","token","nfts","meta",
    "viral","trend","style","fashi","model","actor","movie","shows","stars","space",
    "earth","ocean","river","mount","forest","flora","fauna","plant","fruit","berry",
    "grape","mango","lemon","melon","peach","plums","cherry","dates","olive","onion",
    "carrot","beans","wheat","bread","pizza","pasta","sushi","steak",
    "salad","soups","cakes","candy","sweet","sugar","honey","cream","cheese","butter",
    "water","juice","drink","glass","bottle",
    "table","chair","lamps","clock","watch","phone",
    "doors","walls","roofs","floor","house","homes","rooms","yards","garden","parks",
    "roads","paths","track","trail","drive","rides","bikes","boats","ships","plane",
    "train","buses","taxis","truck","cargo","fleet","wheels","motor","engine","speed",
    "quick","rapid","swift","flash","blaze","spark","flame","burns","heats",
    "colds","snows","storm","rains","cloud","winds","sunny","light","shiny",
    "glows","shine","glare","gleam","moons","comet","orbit",
    "galax","nebul","quark","atoms","force","power","energy",
    "solar","lunar","tidal","waves","sound","noisy","quiet","peace","calms",
    "happy","smile","laugh","bliss","merry","cheer","jolly","jokes",
    "funny","humor","comic","clown","smirk","grins","teeth","mouth","noses",
    "faces","heads","hands","wrist","elbow","knees","ankle","heels",
    "backs","chest","heart","brain","minds","think","knows",
    "learn","study","teach","tutor","coach","guide","expert","maste",
    "elite","prime","super","ultra","mega","giga","hyper","extra","grand",
    "great","major","chief","bosss","ruler","kingg","queen",
    "royal","crown","sword","shield","armor","knight","warrior","fight","battle","combat",
    "siege","forts","tower","locks","keys","vault","safes",
    "banks","chest","boxes","cases","packs","bags","sacks","trunk","crates",
    "tools","knife","blade","razor","drill","hammer","screw","nails","bolts",
    "wires","cords","cable","fiber","laser","radar","sonar","beacon","pulse",
    "codes","bytes","bits","pixel","image","frame","scene","shots","clips","films",
    "reels","tapes","discs","album","songs","lyric","verse","chorus","rhyme",
    "beats","tempo","rhyth","dance","moves","steps","twirl","swirl","swing","salsa",
    "tango","waltz","disco","funky","groov","jazzy","blues","rocks","metal",
    "indie","folks","souls","gospel","choir","opera","arias","sings",
    "vocal","voice","speak","talks","chats","texts","words","terms","names","title",
    "label","brand","logos","marks","signs","badge","flags","posters","cards",
    "decks","plays","rules","score","goals","wins","loses","draws",
    "match","round","final","champ","trophy","medal","prize","award","bonus","gifts",
    "wraps","deals","sales","shops","store","malls","market",
    "stock","share","bonds","funds","asset","value","price","costs","rates",
    "fees","taxes","dues","bills","coins","cents","bucks","zeros",
    "units","items","goods","wares","stuff","thing","parts","piece","slice","chunk",
    "block","brick","stone","rocks","gravel","soils","clays",
    "slime","gooey","stick","glue","paste","resin","oils","fats",
    "paint","tints","shade","hues","color","tones","pales","fades",
    "ashes","smoke","fumes","vapor","steam","mists","foggy",
    "dusky","dawns","dusks","noons","night","darks","black","white","grays",
    "brown","green","blues","pinks","purpl","viole","indig","cyan","teals",
    "amber","beige","cream","ivory","pearl","goldd","silve","bronz","coppe","rusty",
    "iron","steel","alumin","titan","zincs","leads","nickl","cobal","chrom",
    "silic","carbo","oxyge","nitro","hydro","heliu","neon","argon",
    "radon","urani","pluto","radium","polon","bismo","thall","mercu",
    "plati","palla","iridi","osmiu","rheni","tungs","tanta","hafni","zirco",
    "yttri","scand","titani","vana","manga","ferro","nicke","coppe",
    "galli","germa","arsen","selen","bromi","rubid","stron",
    "niobi","molyb","techn","ruthe","rhodi","cadmi","indiu",
    "antim","tellu","iodin","cesiu","bariu","latha","ceriu","prase",
    "neody","prom","samar","europ","gadoli","terbi","dyspr","holmi","erbiu","thuli",
    "ytter","lutet","reniu","bismu","polon","astat","franc","radiu","actin",
    "thori","proto","neptu","ameri","curiu","berke","calif","einst",
    "fermi","mende","nobel","lawre","ruther","dubni","seabo","bohri","hasse","meitn",
    "darms","roent","copern","nihon","flero","mosco","liver","tenne","oganess",
    "alpha","beta","gamma","delta","sigma","omega","theta","kappa","lambda",
    "tauus","upsil","phiss","chiss","psiss","aleph","beth","gimel",
    "dalet","heiss","zayin","chett","tettt","yoddd","kaphh","lamed",
    "nunns","samek","ayinn","pehhh","tsade","qophh","reshe","shinn","tavvv",
    "first","second","third","fourt","fifth","sixth","seven","eight","ninth","tenth",
    "eleven","twelv","thirt","fifte","sixte","ninet","twent",
    "thirt","forty","fifty","sixty","hundr","thous","milli",
    "micro","nanoo","picoo","femto","atto","zepto","yocto","ronna","quetta",
    "kilo","mega","giga","tera","peta","exa","zetta","yotta","bronto","geopa",
    "monday","tuesd","wedne","thurs","frida","satur","sunda","janua","febru","march",
    "april","mayyy","junee","jully","augus","septe","octob","novem","decem","winte",
    "sprin","summe","autum","falls","years","month","weeks","dayss","hours","minut",
    "secon","momen","epoch","eras","times","dates","clock","watch","timer","alarm",
    "agess","cycle","phase","stage","steps","level","grade","rankk","class",
    "order","group","types","kinds","sorts","forms","modes","style","ways","means",
    "tools","aids","helps","fixes","cures","heals","mends","patch","repai","build",
    "makes","creat","shape","molds","casts","forge","weld","glues",
    "tapes","tacks","stitc","sewss","weave","knits","braid","plait","twist",
    "turns","spins","rolls","loops","knots","binds","ties","wraps","folds","bends",
    "curve","arcss","waves","swell","surge","riser","falls","drops","drips","flows",
    "drain","pours","spill","splash","spray","shoot","burst","blast","crash","smash",
    "break","crack","split","snaps","tears","rips","shred","chops","slices","dices",
    "mince","grind","crush","pound","press","squeez","wring","screw","tight",
    "loose","slack","flopp","softt","hardd","firmm","solid","stiff","rigid","tough",
    "rough","coars","crude","rawss","plain","simpl","basic","core","basal",
    "roots","bases","found","grund","basis","start","begin","onset","birth","origi",
    "sourc","cause","reason","motive","drive","might","stren","vigor",
    "energ","zestt","zeall","ardor","fervr","passi","lustt","crave","thirs","hungr",
    "appet","taste","flavo","aroma","scent","smell","odors","reekk","stink",
    "fragr","perfu","balms","incen","myrrh","muskk","civet","casto","beave",
    "whale","jaspe","agate","onyxx","opall","pearls","coral",
    "ivory","ebony","teaks","mahog","walnu","oakss","maple","birch","beech","cedar",
    "pines","firss","spruc","hemlo","yewss","hicko","elmss","popla","willo",
    "cypre","larch","redwo","seqou","baoba","acaci","mimos","wiste","locust","honey",
    "cassia","senna","tamar","carob","mesqu","alder","bassw","linden","tulip","magnol",
    "dogwo","sassa","sourr","bitte","salty","spicy","tangy","zesty","savor",
    "tasty","yummy","delic","gourm","feast","banqu","repas","meals","lunch","dinne",
    "break","brunc","snack","nibbl","munch","crunc","chews","gulps","swall","digest",
    "absor","assim","metab","catab","anabo","synth","groww","devel","matu",
    "ripen","ferme","curee","smoke","dryss","salts","pickl","canss","jars",
    "freez","chill","cools","icess","snows","froze","glaci","polar","arctic","tundr",
    "taiga","alpin","monta","hilly","plain","plate","basin","valle","gorge","canyo",
    "ravine","gulch","wadii","oasis","desert","dune","sands","beach","coast","shore",
    "cliff","bluff","crag","scree","talus","ledge","shelf","reefs","atoll","lagoo",
    "fjord","estua","delta","marsh","swamp","mires","fens","moors","heath",
    "meado","prair","savan","grass","herbs","shrub","bushs","trees","woods","grove",
    "orcha","viney","field","farmm","ranch","range","graze","pastu","crop","yield",
    "harve","reap","sowss","plant","tilll","ploug","harrow","culti","irriga","drain",
    "ferti","manur","compo","mulch","prune","graft","buddd","layer","shoot",
    "leave","stems","barks","twigs","branc","trunk","crowns","canop","folia","blade",
    "petio","stalk","spike","racem","corym","umbel","head","capit","cymes","panicle",
    "drupe","pomes","legum","grain","caryo","nutss","acorn","seeds",
    "spore","pollen","ovule","embry","endos","peric","testa","hilum","radic","plumu",
    "epico","hypoc","cotyl","nodes","inter","budss","axill","termi","later","adven",
    "tapro","fibro","aerial","buttr","tubers","bulbs","corms","rhizo","stolo",
    "runne","sucke","cutti","buddi","tissu","cultu","clone","hybri",
    "varie","speci","genus","famil","order","phylu","kingd","domai",
    "biome","ecosy","habit","niche","troph","produ","consum","decom","scaven","paras",
    "symbi","mutua","commen","ammens","preda","herbi","carniv","omniv","insec","frugi",
    "foliv","necta","polli","graniv","mollu","pisci","sangu","zooph","sapro","detri",
    "litho","chemo","photo","auto","heter","mixo","facul","oblig","aerob","anaer",
    "mesop","therm","psych","halop","acido","alkal","neutr","osmot","xerop","hydro",
    "hygro","mesic","aqua","marin","terre","aeria","arbore","scans","fossor",
    "cursor","volan","natat","amphi","crepu","diurn","noctu","cathe",
    "vespe","matut","anthel","dawns","dusks","darkk",
}

TAKEN_6 = {
    "google","amazon","netflix","spotify","applee","teslaa","spacex","nasa","elon","musk",
    "donald","trump","joebiden","obama","putin","zelen","macron","merkel","boris","johnson",
    "modi","rahul","sachin","dhoni","virat","rohit","messi","ronaldo","neymar","mbappe",
    "lebron","jordan","kobe","curry","durant","harden","westbr","davis","gianni","luka",
    "tatum","embiid","jokic","butler","adeba","herro","lowry","strus","vincent",
    "martin","robinson","rubio","garlan","allen","mobley","markka","levert","osman",
    "lopez","portis","conna","beasl","matthe","highsm",
    "crypto","bitcoin","ethereum","solana","cardano","ripple","litecoin","dogecoin","shiba","monero",
    "binance","coinbase","kraken","bybit","okx","kucoin","huobi","gateio","bitfin",
    "ledger","trezor","metamask","phantom","trust","wallet","safepal","argent","rainbow","coinomi",
    "exodus","atomic","jaxx","mycel","electrum","bitpay","brd","edge","zen","guarda",
    "uniswap","pancake","sushi","curve","aave","compound","maker","dai","tether","usdc",
    "usdt","busd","frax","trueusd","paxos","gemini","circle","centre","wbtc","renbtc",
    "synthe","chainlink","band","tellor","api3","dia","nest","uma","augur","gnosis",
    "polymarket","azuro","betfury","stake","rollbit","roobet","bcgame","bet365","pinnacle",
    "bovada","draftkings","fanduel","betmgm","caesars","pointsbet","wynnbet","barstool","foxbet","unibet",
    "poker","blackjack","roulette","baccarat","craps","slots","bingo","keno","lottery","raffle",
    "jackpot","million","billion","trillion","zillion","gazillion","infinity","eternal","forever","always",
    "never","sometimes","often","rarely","seldom","usually","frequently","occasionally","constantly","periodically",
    "regularly","daily","weekly","monthly","yearly","hourly","nightly","annual","biweekly",
    "fortnight","decade","century","millennium","epoch","eon","age","era","period","stage",
    "phase","cycle","season","term","session","semester","quarter","trimester","half",
    "whole","total","entire","complete","full","partial","incomplete","broken","damaged","destroyed",
    "ruined","wrecked","demolished","devastated","annihilated","obliterated","eradicated","eliminated","removed","deleted",
    "erased","wiped","cleared","cleaned","purged","flushed","drained","emptied","vacated","abandoned",
    "deserted","forsaken","neglected","ignored","overlooked","missed","lost","found","discovered","invented",
    "created","made","built","constructed","assembled","fabricated","manufactured","produced","generated","synthesized",
    "composed","written","authored","penned","drafted","drawn","sketched","painted","sculpted","carved",
    "engraved","etched","printed","published","issued","released","launched","debuted","premiered","introduced",
    "presented","showed","displayed","exhibited","demonstrated","performed","executed","accomplished","achieved","attained",
    "reached","obtained","acquired","gained","earned","won","secured","procured","purchased","bought",
    "sold","traded","exchanged","bartered","swapped","transferred","shifted","moved","relocated","transported",
    "shipped","delivered","sent","mailed","posted","dispatched","forwarded","redirected","routed","guided",
    "led","directed","managed","controlled","regulated","governed","ruled","commanded","ordered","dictated",
    "prescribed","recommended","suggested","advised","counseled","consulted","informed","notified","alerted","warned",
    "cautioned","reminded","prompted","urged","encouraged","motivated","inspired","stimulated","provoked","triggered",
    "caused","induced","forced","compelled","obliged","required","demanded","requested","asked","questioned",
    "queried","inquired","investigated","examined","inspected","checked","verified","confirmed","validated","authenticated",
    "certified","accredited","licensed","approved","authorized","permitted","allowed","granted","given","provided",
    "supplied","furnished","equipped","armed","prepared","ready","set","go","start","begin",
    "commence","initiate","originate","generate","produce","create","form","shape","mold","cast",
    "forge","weld","solder","braze","glue","paste","tape","tack","staple","stitch",
    "sew","weave","knit","crochet","braid","plait","twist","turn","spin","roll",
    "loop","knot","bind","tie","wrap","fold","bend","curve","arch","wave",
    "swell","surge","rise","fall","drop","drip","flow","stream","run","pour",
    "spill","splash","spray","shoot","burst","blast","crash","smash","break","crack",
    "split","snap","tear","rip","shred","chop","slice","dice","mince","grind",
    "crush","pound","press","squeeze","wring","twist","screw","tighten","loosen","slacken",
    "flop","soften","harden","firm","solidify","stiffen","toughen","roughen","coarsen","crudify",
    "simplify","complicate","complexify","sophisticate","refine","purify","cleanse","clarify","filter","strain",
    "sift","sort","classify","categorize","organize","arrange","order","systematize","structure","format",
    "layout","design","plan","scheme","plot","diagram","chart","graph","map","model",
    "prototype","sample","specimen","example","instance","case","illustration","demonstration","exhibition","display",
    "show","presentation","performance","execution","accomplishment","achievement","attainment","realization","fulfillment","completion",
    "conclusion","termination","cessation","end","finish","close","closure","ending","finale","epilogue",
    "aftermath","consequence","result","outcome","effect","impact","influence","affect","change","alter",
    "modify","adjust","adapt","convert","transform","transfigure","metamorphose","evolve","develop","grow",
    "mature","ripen","age","ferment","cure","smoke","dry","salt","pickle","can",
    "jar","bottle","freeze","chill","cool","ice","snow","frost","glaciate","polarize",
    "magnetize","electrify","ionize","catalyze","oxidize","reduce","hydrolyze","dehydrate","hydrate","saturate",
    "dissolve","melt","fuse","weld","solder","braze","anneal","temper","harden","quench",
    "polish","buff","shine","gloss","glaze","varnish","lacquer","paint","stain","dye",
    "tint","tone","shade","hue","color","pigment","dyestuff","colorant","stain","tinge",
    "touch","trace","hint","suggestion","implication","inference","deduction","conclusion","judgment","decision",
    "verdict","ruling","finding","determination","resolution","settlement","agreement","contract","treaty","pact",
    "accord","concord","harmony","unity","solidarity","cohesion","adhesion","coherence","consistency","congruity",
    "compatibility","conformity","compliance","obedience","submission","yielding","surrender","capitulation","defeat","loss",
    "failure","deficiency","lack","absence","want","need","requirement","necessity","essential","prerequisite",
    "condition","stipulation","provision","clause","term","article","section","paragraph","sentence","phrase",
    "word","letter","character","symbol","sign","mark","token","emblem","badge","insignia",
    "logo","brand","trademark","copyright","patent","license","permit","charter","franchise","concession",
    "privilege","right","entitlement","claim","title","deed","document","record","file","dossier",
    "archive","registry","catalog","directory","index","list","roll","roster","schedule","timetable",
    "calendar","agenda","itinerary","program","syllabus","curriculum","course","lesson","lecture","seminar",
    "workshop","tutorial","training","drill","exercise","practice","rehearsal","preparation","readiness","fitness",
    "health","wellness","wholeness","soundness","strength","vigor","vitality","energy","force","power",
    "might","potency","capacity","capability","ability","skill","talent","gift","aptitude","faculty",
    "knack","dexterity","adroitness","deftness","proficiency","expertise","mastery","command","control","dominion",
    "authority","jurisdiction","sway","influence","leverage","clout","pull","weight","importance","significance",
    "consequence","moment","weightiness","gravity","seriousness","solemnity","dignity","majesty","grandeur",
    "magnificence","splendor","glory","brilliance","radiance","luster","sheen","glow","gleam","glint",
    "sparkle","twinkle","shimmer","glimmer","flicker","flash","flare","blaze","flame","fire",
    "inferno","conflagration","holocaust","cataclysm","catastrophe","disaster","calamity","tragedy","misfortune","adversity",
    "hardship","difficulty","trouble","problem","issue","matter","concern","worry","anxiety","stress",
    "tension","pressure","strain","burden","load","weight","onus","responsibility","duty","obligation",
    "commitment","dedication","devotion","allegiance","loyalty","fidelity","faithfulness","constancy","steadfastness","perseverance",
    "persistence","tenacity","determination","resolve","resolution","will","volition","choice","option","alternative",
    "possibility","probability","likelihood","chance","odds","prospect","hope","expectation","anticipation","aspiration",
    "ambition","goal","aim","objective","target","mark","bullseye","destination","terminus","endpoint",
    "boundary","border","frontier","limit","bounds","confines","perimeter","circumference","periphery","edge",
    "brink","verge","threshold","doorstep","gate","portal","entrance","entry","access","admission",
    "ingress","introduction","initiation","induction","installation","investiture","coronation","enthronement","inauguration","launch",
    "debut","premiere","opening","beginning","start","commencement","inception","genesis","origin","source",
    "root","basis","foundation","groundwork","cornerstone","keystone","linchpin","mainstay","pillar","support",
    "prop","stay","brace","buttress","reinforcement","backing","assistance","help","aid","succor",
    "relief","comfort","ease","alleviation","mitigation","palliation","remission","abatement","subsidence","decline",
    "decrease","reduction","diminution","lessening","lowering","dropping","falling","sinking","descending","plunging",
    "diving","plummeting","nosediving","crashing","collapsing","caving","giving","yielding","buckling","breaking",
    "fracturing","shattering","splintering","fragmenting","disintegrating","crumbling","decaying","rotting","decomposing","putrefying",
    "fermenting","brewing","cooking","baking","roasting","grilling","frying","sautéing","simmering","boiling",
    "steaming","poaching","braising","stewing","casserole","soufflé","omelet","frittata","quiche","tart",
    "pie","cake","pudding","custard","mousse","sorbet","gelato","sherbet","parfait","trifle",
    "tiramisu","baklava","strudel","croissant","baguette","brioche","focaccia","ciabatta","pita","naan",
    "tortilla","arepa","empanada","pierogi","dumpling","wonton","gyoza","mandu","momos","samosa",
    "pakora","bhaji","bonda","vada","idli","dosa","uttapam","pongal","upma","poha",
    "sevai","kheer","payasam","halwa","ladoo","barfi","peda","jalebi","gulab","jamun",
    "rasgulla","sandesh","mishti","doi","shrikhand","amrak","aamras","lassi","chaas","buttermilk",
    "sharbat","falooda","thandai","badam","khus","rooh","afza","jaljeera",
    "neembu","pani","kokum","sol","kadhi","rasam","sambar","dal","sambhar","vathal",
    "kuzhambu","kootu","poriyal","thoran","mezhukkupuratti","avial","olan","kalan","erissery","puliserry",
    "moru","curry","molee","fish","meen","kari","chicken","mutton","beef","pork",
    "prawn","crab","lobster","squid","cuttle","octopus","oyster","clam","mussel","scallop",
    "abalone","conch","whelk","periwinkle","limpet","barnacle","krill","plankton","coral","sponge",
    "jellyfish","anemone","starfish","urchin","seacucumber","sealily","feather","worm","leech","slug",
    "snail","ark","tellin","venus","quahog",
    "geoduck","razor","jackknife","surf","coquina","donax","bean","wing","jingle","file",
    "lucine","sunrise","crossbarred","tiger","chocolate","strawberry","vanilla","mint","lemon","orange",
    "banana","coconut","pineapple","mango","papaya","guava","passion","dragon","kiwi","lychee",
    "rambutan","longan","durian","jackfruit","breadfruit","plantain","tamarind","date","fig","pomegranate",
    "persimmon","quince","medlar","loquat","kumquat","calamondin","yuzu","sudachi","kabosu","lime",
    "grapefruit","pomelo","tangelo","ugli","minneola","ortanique","clementine","satsuma","tangerine",
    "mandarin","calamansi","finger","citron","bergamot","etrog","buddha","hand",
}

class UsernameChecker:
    def __init__(self):
        self.session = None
        self.semaphore = asyncio.Semaphore(CONCURRENT_LIMIT)
        self.cache = {}
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    async def init_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(headers=self.headers)

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def check_telegram(self, username):
        try:
            url = f"https://t.me/{username}"
            async with self.semaphore:
                async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=5), allow_redirects=True) as resp:
                    text = await resp.text()
                    tl = text.lower()
                    if resp.status in (404, 302):
                        return {"status": "free", "banned": False}
                    banned = ["deleted","terminated","banned"]
                    if any(b in tl for b in banned):
                        return {"status": "taken", "banned": True}
                    if resp.status == 200:
                        taken = ['tgme_page_photo','tgme_page_title','tgme_page_description','tgme_page_extra']
                        free = ["if you have telegram","no messages here"]
                        is_taken = any(t in tl for t in taken)
                        is_free = any(f in tl for f in free)
                        if is_taken and not is_free:
                            return {"status": "taken", "banned": False}
                        return {"status": "free", "banned": False}
                    return {"status": "free", "banned": False}
        except:
            return {"status": "error", "banned": False}

    async def check_fragment(self, username):
        try:
            url = f"https://fragment.com/username/{username}"
            async with self.semaphore:
                async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=5), allow_redirects=True) as resp:
                    text = await resp.text()
                    tl = text.lower()
                    if resp.status == 404:
                        return {"on_sale": False, "status": "not_listed"}
                    sale = ["auction","for sale","buy now","current bid","place bid","ton","ends in","collectible"]
                    is_sale = any(s in tl for s in sale)
                    return {"on_sale": is_sale, "status": "auction" if is_sale else "not_listed"}
        except:
            return {"on_sale": False, "status": "error"}

    async def check_username(self, username):
        if username in self.cache:
            return self.cache[username]
        tg = await self.check_telegram(username)
        if tg["status"] != "free" or tg["banned"]:
            r = {"username": username, "available": False, "telegram_status": tg["status"], "fragment_status": "skipped", "banned": tg["banned"], "on_sale": False}
            self.cache[username] = r
            return r
        fr = await self.check_fragment(username)
        avail = not fr["on_sale"] and not tg["banned"]
        r = {"username": username, "available": avail, "telegram_status": tg["status"], "fragment_status": fr["status"], "banned": tg["banned"], "on_sale": fr["on_sale"]}
        self.cache[username] = r
        return r

    async def check_batch(self, usernames):
        await self.init_session()
        tasks = [self.check_username(u) for u in usernames]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if isinstance(r, dict)]


def generate_letter_usernames(length, count=500):
    letters = string.ascii_lowercase
    usernames = set()
    vowels = "aeiou"
    consonants = "".join(c for c in letters if c not in vowels)
    taken_set = TAKEN_5 if length == 5 else TAKEN_6

    while len(usernames) < count:
        if random.random() > 0.3:
            username = "".join(random.choices(letters, k=length))
        else:
            username = ""
            for i in range(length):
                if i % 2 == 0:
                    username += random.choice(consonants)
                else:
                    username += random.choice(vowels)
        if len(username) == length and username.isalpha() and username not in taken_set:
            usernames.add(username)
    return list(usernames)


def generate_word_variations(word):
    letters = string.ascii_lowercase
    variations = []
    for _ in range(50):
        prefix = "".join(random.choices(letters, k=random.randint(1, 2)))
        var = f"{prefix}{word}"
        if 5 <= len(var) <= 32 and var.isalpha():
            variations.append(var)
    for _ in range(50):
        suffix = "".join(random.choices(letters, k=random.randint(1, 2)))
        var = f"{word}{suffix}"
        if 5 <= len(var) <= 32 and var.isalpha() and var not in variations:
            variations.append(var)
    for _ in range(40):
        pre = "".join(random.choices(letters, k=1))
        suf = "".join(random.choices(letters, k=1))
        var = f"{pre}{word}{suf}"
        if 5 <= len(var) <= 32 and var.isalpha() and var not in variations:
            variations.append(var)
    for _ in range(30):
        pre = "".join(random.choices(letters, k=2))
        suf = "".join(random.choices(letters, k=2))
        var = f"{pre}{word}{suf}"
        if 5 <= len(var) <= 32 and var.isalpha() and var not in variations:
            variations.append(var)
    return variations[:170]


SEARCH_ANIMATIONS = [
    "🔍 Проверяется @{username}...",
    "⚡ Анализируется @{username}...",
    "🔎 Сканируется @{username}...",
    "📡 Запрос к серверам: @{username}...",
    "🌐 Проверка Fragment: @{username}...",
    "✨ Тестируется @{username}...",
    "🎯 Верификация @{username}...",
    "🛡️ Проверка бана: @{username}...",
]

async def animate_search(message, context, checker, usernames):
    start_time = datetime.now()
    checked = 0
    found = []
    total = len(usernames)
    batches = [usernames[i:i + BATCH_SIZE] for i in range(0, total, BATCH_SIZE)]

    for batch in batches:
        results = await checker.check_batch(batch)
        checked += len(batch)
        for r in results:
            if r.get("available"):
                found.append(r)

        if checked % (BATCH_SIZE * 2) == 0 or checked == total or len(found) >= MAX_RESULTS:
            time_elapsed = (datetime.now() - start_time).seconds
            current = batch[-1] if batch else "..."
            anim_text = random.choice(SEARCH_ANIMATIONS).format(username=current)
            progress = f"\n\n📊 Проверено: {checked}/{total}\n⏱️ Прошло: {time_elapsed}с\n✅ Найдено: {len(found)}"
            try:
                await message.edit_text(anim_text + progress, parse_mode="HTML")
            except:
                pass

        if len(found) >= MAX_RESULTS:
            break
        await asyncio.sleep(CHECK_DELAY)
        if (datetime.now() - start_time).seconds >= SEARCH_TIMEOUT:
            break

    return found


checker = UsernameChecker()

async def start(update, context):
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("🔠 Поиск 5-буквенных", callback_data="search_5")],
        [InlineKeyboardButton("🔠 Поиск 6-буквенных", callback_data="search_6")],
        [InlineKeyboardButton("🔤 Поиск по слову", callback_data="search_word")],
    ]
    if user.id == OWNER_ID:
        keyboard.append([InlineKeyboardButton("⚙️ Админ-панель", callback_data="admin")])

    welcome_text = (
        f"👋 Привет, <b>{user.first_name}</b>!\n\n"
        f"🤖 Я бот для поиска <b>свободных юзернеймов</b> Telegram.\n\n"
        f"✨ <b>Что я проверяю:</b>\n"
        f"  • Не занят в Telegram ✅\n"
        f"  • Не на продаже на Fragment ✅\n"
        f"  • Не забанен ✅\n"
        f"  • <b>Только буквы</b>, без цифр ✅\n\n"
        f"👇 <b>Выбери действие:</b>"
    )
    await update.message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


async def button_handler(update, context):
    query = update.callback_query
    await query.answer()

    if query.data == "search_5":
        await query.edit_message_text(
            "🔍 <b>Начинаю поиск 5-буквенных юзернеймов...</b>\n\n"
            "⏳ Генерация списка кандидатов...", 
            parse_mode="HTML"
        )
        usernames = generate_letter_usernames(5, 500)
        msg = await query.edit_message_text(
            "🔍 <b>Поиск запущен!</b>\n\n"
            "🚀 Проверяю первую партию юзернеймов...", 
            parse_mode="HTML"
        )
        found = await animate_search(msg, context, checker, usernames)

        if found:
            text = "🎉 <b>Найдены свободные 5-буквенные юзернеймы!</b>\n\n"
            for i, r in enumerate(found[:MAX_RESULTS], 1):
                text += f"{i}. <code>@{r['username']}</code> ✅\n"
            text += "\n💡 <b>Совет:</b> Проверьте их сразу — свободные короткие юзернеймы разбирают за секунды!"
        else:
            text = (
                "😔 <b>Свободных 5-буквенных юзернеймов не найдено.</b>\n\n"
                "🔄 Попробуйте ещё раз — каждый запрос генерирует новые случайные комбинации!"
            )
        keyboard = [
            [InlineKeyboardButton("🔄 Повторить поиск", callback_data="search_5")],
            [InlineKeyboardButton("🔙 В меню", callback_data="back")]
        ]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    elif query.data == "search_6":
        await query.edit_message_text(
            "🔍 <b>Начинаю поиск 6-буквенных юзернеймов...</b>", 
            parse_mode="HTML"
        )
        usernames = generate_letter_usernames(6, 500)
        msg = await query.edit_message_text(
            "🔍 <b>Поиск запущен!</b>\n\n"
            "🚀 Проверяю первую партию юзернеймов...", 
            parse_mode="HTML"
        )
        found = await animate_search(msg, context, checker, usernames)

        if found:
            text = "🎉 <b>Найдены свободные 6-буквенные юзернеймы!</b>\n\n"
            for i, r in enumerate(found[:MAX_RESULTS], 1):
                text += f"{i}. <code>@{r['username']}</code> ✅\n"
            text += "\n💡 Проверьте их сразу!"
        else:
            text = (
                "😔 <b>Свободных 6-буквенных юзернеймов не найдено.</b>\n\n"
                "🔄 Попробуйте ещё раз!"
            )
        keyboard = [
            [InlineKeyboardButton("🔄 Повторить поиск", callback_data="search_6")],
            [InlineKeyboardButton("🔙 В меню", callback_data="back")]
        ]
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    elif query.data == "search_word":
        await query.edit_message_text(
            "🔤 <b>Поиск по слову</b>\n\n"
            "Введите слово <b>на английском</b>, и я найду варианты с префиксом и суффиксом.\n\n"
            "📌 <b>Пример:</b> если ввести <code>apple</code>, я найду:\n"
            "  • <code>xaapple</code> (префикс)\n"
            "  • <code>applexy</code> (суффикс)\n"
            "  • <code>xappley</code> (префикс+суффикс)\n\n"
            "📝 <b>Введите слово:</b>",
            parse_mode="HTML"
        )
        return WORD_INPUT

    elif query.data == "back":
        await start_from_query(query)

    elif query.data == "admin":
        if query.from_user.id != OWNER_ID:
            await query.answer("❌ Нет доступа!", show_alert=True)
            return
        text = (
            "⚙️ <b>Админ-панель</b>\n\n"
            f"👤 Владелец ID: <code>{OWNER_ID}</code>\n"
            f"🤖 Бот работает в штатном режиме.\n\n"
            f"📊 Здесь можно добавить:\n"
            f"  • Статистику пользователей\n"
            f"  • Логи проверок\n"
            f"  • Управление подписками\n\n"
            f"🔧 Для изменений — редактируй код в GitHub!"
        )
        keyboard = [[InlineKeyboardButton("🔙 В меню", callback_data="back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


async def start_from_query(query):
    keyboard = [
        [InlineKeyboardButton("🔠 Поиск 5-буквенных", callback_data="search_5")],
        [InlineKeyboardButton("🔠 Поиск 6-буквенных", callback_data="search_6")],
        [InlineKeyboardButton("🔤 Поиск по слову", callback_data="search_word")],
    ]
    if query.from_user.id == OWNER_ID:
        keyboard.append([InlineKeyboardButton("⚙️ Админ-панель", callback_data="admin")])

    welcome_text = (
        f"🤖 <b>Бот для поиска свободных юзернеймов</b>\n\n"
        f"✨ <b>Возможности:</b>\n"
        f"  • 5-буквенные юзернеймы\n"
        f"  • 6-буквенные юзернеймы\n"
        f"  • Поиск по слову (префикс/суффикс)\n"
        f"  • Проверка Fragment + Telegram + Бан\n\n"
        f"👇 <b>Выбери действие:</b>"
    )
    await query.edit_message_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


async def word_input_handler(update, context):
    word = update.message.text.strip().lower()

    if not word.isalpha():
        await update.message.reply_text(
            "❌ <b>Ошибка!</b> Введите только буквы (a-z), без цифр, пробелов и символов!\n\n"
            "🔄 Попробуйте снова:",
            parse_mode="HTML"
        )
        return WORD_INPUT

    if len(word) < 3:
        await update.message.reply_text(
            "❌ Слово слишком короткое! Минимум 3 буквы.\n\n"
            "🔄 Попробуйте снова:",
            parse_mode="HTML"
        )
        return WORD_INPUT

    if len(word) > 20:
        await update.message.reply_text(
            "❌ Слово слишком длинное! Максимум 20 букв.\n\n"
            "🔄 Попробуйте снова:",
            parse_mode="HTML"
        )
        return WORD_INPUT

    msg = await update.message.reply_text(
        f"🔍 <b>Ищу варианты для слова '{word}'...</b>\n\n"
        f"⏳ Генерация комбинаций...", 
        parse_mode="HTML"
    )
    usernames = generate_word_variations(word)
    await msg.edit_text(
        f"🔍 <b>Поиск по слову '{word}'</b>\n\n"
        f"🚀 Начинаю проверку <b>{len(usernames)}</b> вариантов...", 
        parse_mode="HTML"
    )
    found = await animate_search(msg, context, checker, usernames)

    if found:
        text = f"🎉 <b>Найдены свободные варианты для '{word}'!</b>\n\n"
        for i, r in enumerate(found[:MAX_RESULTS], 1):
            text += f"{i}. <code>@{r['username']}</code> ✅\n"
        text += "\n💡 <b>Совет:</b> Проверьте сразу — юзернеймы быстро разбирают!"
    else:
        text = (
            f"😔 <b>Для слова '{word}' свободных вариантов не найдено.</b>\n\n"
            f"🔄 Попробуйте другое слово!"
        )
    keyboard = [
        [InlineKeyboardButton("🔤 Новое слово", callback_data="search_word")],
        [InlineKeyboardButton("🔙 В меню", callback_data="back")]
    ]
    await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    return ConversationHandler.END


async def cancel(update, context):
    await update.message.reply_text("❌ Отменено. Возвращаюсь в меню...")
    await start(update, context)
    return ConversationHandler.END


async def health_check(request):
    return web.Response(text="✅ Бот работает! Username Finder Bot is alive.", status=200)


async def run_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"🌐 Веб-сервер запущен на порту {PORT}")


async def main():
    web_task = asyncio.create_task(run_web_server())

    application = Application.builder().token(BOT_TOKEN).build()

    word_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^search_word$")],
        states={
            WORD_INPUT: [MessageHandler(filters.TEXT & (~filters.COMMAND), word_input_handler)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(word_conv)
    application.add_handler(CallbackQueryHandler(button_handler))

    logger.info("🤖 Бот запущен! Ожидаю сообщения...")

    await application.initialize()
    await application.start()
    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Остановка бота...")
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        await checker.close()
        web_task.cancel()
        try:
            await web_task
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    asyncio.run(main())
