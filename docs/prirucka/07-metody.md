# 07 · Rejstřík metod

Každá metoda jádra a její role **v procesu zpracování** — ne co vrací, ale
proč tam je. Kde má metoda docstring, bere se jeho první věta.

Soukromé metody (`_jmeno`) jsou uvedené taky, protože nesou rozhodnutí,
která jsou jinde vidět jen jako důsledek.


## `core/agents/base.py`

*Specializovaní agenti — každý jednu doménu.*

| metoda | role v procesu |
|---|---|
| **`class Naveska`** | Co agent na místě v textu našel. |
| `Naveska.do_slovniku()` | návěska do JSON pro zápis do tokenu |
| **`class Agent`** | Expert na jednu doménu. Čte větu, vrací návěsky. |
| `Agent.najdi()` | Nálezy v jedné větě. Věta je seznam tokenů {form, upos, acts, …}. |
| `Agent.oznac()` | Zapíše nálezy do věty. Typ do `acts`, hodnota mimo ně. |
| `v_zavorce()` | Je token uvnitř závorky? |
| `je_cele_cislo()` | Dá se ten tvar přečíst jako celé číslo? |
| `je_cislo()` | je token číslovka? (UPOS nebo NumType) |

## `core/agents/bio.py`

*Biografická závorka: „Osoba ( datum místo – datum místo )" → narození a úmrtí.*

| metoda | role v procesu |
|---|---|
| **`class Bio`** |  |
| `Bio.najdi()` | biografická závorka za jménem → narození a úmrtí |
| `Bio.je_definicni()` | Úvodní věta životopisu: „Osoba ( … – … ) byl/byla …". |
| `Bio.najit_zavorku()` | Závorka hned za jménem, uvnitř s pomlčkou. Vrací (od, do, dělicí). |
| `Bio.najit_delic()` | Pomlčka, která dělí narození od úmrtí — ne každá pomlčka uvnitř. |
| `Bio.najit_konec()` | párová závorka, i vnořená |
| `Bio.vytezit()` | Z půlky závorky rok a místo. Prázdná půle nevrací nic — u žijícího |
| `Bio.najit_rok()` | čtyřmístné číslo v rozsahu let |
| `Bio.najit_misto()` | PROPN s NameType=Geo; osobní jméno se vyloučí |

## `core/agents/chronos.py`

*Chronos — agent ČAS.*

| metoda | role v procesu |
|---|---|
| **`class Chronos`** |  |
| `Chronos.je_rok()` | čtyřmístné číslo v rozsahu 1000–2100 |
| `Chronos.je_den()` | Den v datu se v češtině píše s tečkou: „28.". UDPipe tečku |
| `Chronos.mesic()` | jméno měsíce → číslo, z jazykového profilu |
| `Chronos.najdi()` | data a roky ve větě, mimo závorky |
| `Chronos.datum_od()` | Plné datum „28 . března 1914" nebo „28. března". |
| `Chronos.rok_od_pozice()` | Samotný rok, případně i s uvozujícím slovem („v roce 1914"). |

## `core/agents/metron.py`

*Metron — agent POČET a MÍRA.*

| metoda | role v procesu |
|---|---|
| **`class Metron`** |  |
| `Metron.je_rok()` | rok patří Chronosovi, ne počtům |
| `Metron.najdi()` | počty a míry, bez roků a bez závorek |
| `Metron.hodnota()` | Číslicí přesně, slovem jen jako tvar — číslovkový lexikon zatím |

## `core/agents/topos.py`

*Topos — agent MÍSTO.*

| metoda | role v procesu |
|---|---|
| **`class Topos`** |  |
| `Topos.je_misto()` | NameType=Geo, případně gazetteer |
| `Topos.najdi()` | místa ve větě, mimo závorky |

## `core/answers.py`

*Odpověď na otázku o obsahu korpusu — a hlavně: CO SE AKTIVUJE.*

| metoda | role v procesu |
|---|---|
| **`class Odpovidac`** | Otázka dovnitř, aktivace a kandidáti ven. |
| `Odpovidac._sestavit_navesky()` | Věta → typ → rozsahy, které agenti označili. |
| `Odpovidac._sestavit_entity()` | Entita → věty, ve kterých o ní je řeč. Klíč je z `Ent=`, protože |
| `Odpovidac.obsahove_tvary()` | slova otázky, která o obsahu něco říkají |
| `Odpovidac.vety_tvaru()` | ve kterých větách faktů tvar svítí — tohle je ta aktivace |
| `Odpovidac.najit_entitu()` | Jméno z otázky → klíč entity. Stačí, když sedí příjmení. |
| `Odpovidac.sedi_cele_jmeno()` | Sedí VŠECHNA jména z otázky na jednu entitu? |
| `Odpovidac.jmena_v_otazce()` | Slova s velkým písmenem uprostřed otázky. V češtině je to slušné |
| `Odpovidac.rozsvitit()` | co se z otázky aktivuje: entita, tvary, pole |
| `Odpovidac.rozsirit()` | Věty, které tvar zasáhne PŘES ZNALOST. Potomek se hledá napřed |
| `Odpovidac.je_na_obsah()` | ptá se otázka na obsah korpusu, nebo na vztah? |
| `Odpovidac.odpovedet()` | celá cesta: aktivace → pole → kandidáti |
| `Odpovidac.sebrat()` | Úseky daného druhu ve větách pole. |
| `Odpovidac.text_rozsahu()` | úsek věty jako text |
| `Odpovidac.text_vety()` | celá věta jako text — kontext ke kandidátovi |

## `core/compose.py`

*Krok 5 workflow: složit otázku ze slovníku, bez věty.*

| metoda | role v procesu |
|---|---|
| **`class Vzor`** | Rozdělaná otázka. `kotva` je index tázacího tvaru, -1 = zatím žádný. |
| `Vzor.je_hotovy()` | má vzor slova, kotvu i cíl? |
| `Vzor.tazaci_tvar()` | slovo na kotvě — na co se ptáme |
| `Vzor.do_slovniku()` | vzor do JSON pro uložení mapování |
| `Vzor.ze_slovniku()` | vzor z uloženého mapování |
| **`class Skladac`** | Sestavuje vzor a umí z něj složit vektor. |
| `Skladac.zvolit_kotvu()` | přidá tázací tvar a označí ho za kotvu |
| `Skladac.pridat_slovo()` | další slovo na konec vzoru |
| `Skladac.odebrat_slovo()` | Odebrání slova PŘED kotvou kotvu posune; odebrání kotvy ji zruší, |
| `Skladac.prepnout_cil()` | cílový tvar na faktové straně |
| `Skladac.vycistit()` | zahodí rozdělaný vzor |
| `Skladac.spocitat_offsety()` | pozice slov vůči kotvě |
| `Skladac.slozit_vektor()` | Vektor složené otázky i s tím, co je na něm nejisté. |
| `Skladac.vypsat_aktivace_tvaru()` | Naklikané slovo si aktivace přinese ze slovníku. Kde má tvar víc |
| `Skladac.spocitat_jistotu()` | kolik sad aktivací tvar má; víc = hádá se |
| `Skladac.najit_shodnou_sablonu()` | existuje šablona s tímhle vektorem? |
| `Skladac.popsat_vzor()` | vzor k zobrazení |
| `popsat_zaznam()` | Popis uložené dvojice. Starší záznamy kotvu nemají — jsou to množiny. |

## `core/config.py`

*Konfigurace — hlavně kde leží data.*

| metoda | role v procesu |
|---|---|
| **`class Config`** | Porty jsou schválně mimo obvyklá čísla: 8000, 8001 a 8112 už na |
| `Config.udpipe()` | adresa vlastní instance UDPipe |
| `Config.cesta_logu()` | kam se píše log |
| `Config.slozka_behu()` | Kam se ukládají pid soubory a logy běžících procesů. |
| `Config.cesta_znalosti()` | Tvrzení přijatá z dialogu. Nejde přes šev Uloziste: to je rozhraní |
| `Config.cesta_svazu()` | Typový svaz z Wikidat — podklad, na který dialog navazuje. |
| `Config.absolutni()` | relativní cesta se zakotví ke kořeni projektu |
| `Config.slozka()` | podadresář datové struktury — každý typ svůj |
| `Config.zalozit_slozky()` | vytvoří datové adresáře, když chybí |
| `Config.nacist()` | vrstvení: výchozí < config.json < POLE2_* < parametry |
| `Config._ze_souboru()` | hodnoty z config.json |
| `Config._z_prostredi()` | hodnoty z proměnných POLE2_* |
| `Config.do_slovniku()` | konfigurace k vypsání |

## `core/derived.py`

*Odvozené vertikály — týž atribut v hrubším rozlišení.*

| metoda | role v procesu |
|---|---|
| **`class Odvozena`** | Jedna hrubá vrstva nad jednou jemnou. |
| `Odvozena.hodnoty()` | Všechny hodnoty, kterých může nabýt — kvůli katalogu vertikál. |
| `Odvozena.vertikaly()` | sloupce, které vrstva přidá do katalogu |
| `Odvozena.odvodit()` | Hrubá hodnota pro tenhle token, nebo None, když zdroj chybí. |
| `_mapa()` | seznam hodnot → jedna hrubá hodnota |
| `vertikaly_odvozenych()` | Sloupce, které se přidají do katalogu. Na konec — kanonické pořadí je |
| `jmena_odvozenych()` | jména hrubých sloupců — k odfiltrování při ukládání |
| `bez_odvozenych()` | Katalog očištěný o hrubé vrstvy — k uložení. |
| `ocistit_korpus()` | Věty bez hrubých vrstev — k uložení. |

## `core/dialog.py`

*Rozhovor jako objekt: věta dovnitř, záznam ven.*

| metoda | role v procesu |
|---|---|
| **`class Zaznam`** | Jeden tah rozhovoru. Drží i to, co se NEstalo — odmítnutí a nejasnost |
| `Zaznam.do_slovniku()` | tah rozhovoru do JSON pro prohlížeč |
| **`class Rozhovor`** |  |
| `Rozhovor.poslat()` | Jeden řádek od člověka. Rozhovor, který čeká na rozhodnutí, další |
| `Rozhovor.z_pole()` | Odpověď z korpusu. Vrací KANDIDÁTY, ne jedno slovo: šablona je |
| `Rozhovor.prijmout()` | tvrzení do znalosti, otázku do pole, jinak nejasnost |
| `Rozhovor.rozhodnout()` | Odpověď na nejasnost. Bez čekající nejasnosti se nedá rozhodovat. |
| `Rozhovor.preskocit()` | nejasnost zahodit bez rozhodnutí |
| `Rozhovor.zapsat_tvrzeni()` | hrana do znalosti a uložení |
| `Rozhovor.odpovedet()` | dotaz ve tvaru „? X Y“ |
| `Rozhovor.rozdelit()` | Kde v „Je Šmoula pohádková bytost?" končí první pojem. |
| `Rozhovor.odpovedet_pojmy()` | Pojmy už jsou lemmatizované — sem chodí i česky položená otázka. |
| `Rozhovor.rodokmen()` | dotaz ve tvaru „?? X“ |
| `Rozhovor.zaradit()` | Čím vším pojem je. Odpověď na „co je X?" i na „?? X". |
| `Rozhovor.zapsat()` | záznam do historie |
| `Rozhovor.ceka_na_rozhodnuti()` | visí nedořešená nejasnost? |
| `Rozhovor.vypsat_historii()` | přepis rozhovoru pro prohlížeč |
| `Rozhovor.vypsat_znalost()` | Znalost k vykreslení: uzly, hrany a čísla. |
| `Rozhovor.vypsat_stav()` | historie + znalost + poslední nález + čekání |
| `Rozhovor.zapomenout()` | Zahodí, co se rozhovorem naučilo. Podklad ze svazu zůstane — ten |

## `core/export.py`

*Převod modelu na JSON. Patří do knihovny, ne do serveru — jiný program*

| metoda | role v procesu |
|---|---|
| **`class Vyrez`** | Kolik toho jde ven. `vet=None` znamená celý korpus. |
| `Vyrez.do_vety()` | konec okna, nebo None u celého korpusu |
| `Vyrez.obsahuje()` | je věta uvnitř okna? |
| `Vyrez.je_cely()` | žádné omezení — posílá se všechno |
| **`class Prevod`** | Přečíslování z globálních indexů na indexy výřezu. |
| `Prevod._sestavit()` | mapy globální → místní index, řádky i věty |
| `Prevod.radek()` | globální index řádku → místní, nebo None |
| `Prevod.veta()` | globální číslo věty → místní |
| `Prevod.prosit_radky()` | Jen řádky uvnitř výřezu, přečíslované. |
| `Prevod.pocet_vet()` | kolik vět je ve výřezu |
| `radky_strany()` | Rozvržení pole: na řádek dvojice [věta, pořadí tokenu] a null místo |
| `sablony_strany()` | Jen šablony, kterých se výřez dotkne. `celkem` je ale z celého pole — |
| `vazby_strany()` | vazby slovo↔šablona, přečíslované a s globálním počtem |
| `sloty_strany()` | Offsety slotů na střed. Slot mířící mimo výřez se pošle jako null — |
| `slovnik_ven()` | Počty výskytů jsou GLOBÁLNÍ, seznamy vět jen z výřezu. Tvar, který |
| `korpusy_ven()` | Věty tak, jak je vidí jádro — tedy i s hrubými vrstvami a už bez |
| `cisla_strany()` | Čísla jsou z CELÉHO pole. Výřez se hlásí zvlášť, ať je vidět, kolik |
| `strana_ven()` | jedna strana pole do JSON přes Prevod |
| `prehled_sablon()` | Vzory samy o sobě, bez mřížky. |
| `pole_ven()` | Celý model. `s_korpusy` přiloží i věty — prohlížeč je potřebuje jen |

## `core/field.py`

*Fasáda celého průchodu. Tohle si naimportuje program, který chce pole.*

| metoda | role v procesu |
|---|---|
| **`class Pole`** |  |
| `Pole.postavit()` | Celý průchod. Když se od minule nic nezměnilo, nedělá nic. |
| `Pole.vypsat_vertikaly()` | Katalog sloupců: uložené plus hrubé vrstvy nad nimi. |
| `Pole.zapomenout_katalog()` | Katalog se změnil zvenku — zahodit, ať se složí znovu. |
| `Pole.pripravit_zdroj()` | šev ZdrojAktivaci; podstrčený zvenku má přednost |
| `Pole.pripravit_sitko()` | Vertikály sítko potřebuje kvůli skupinám — `FEATS` propustí celou |
| `Pole.rozprostrit()` | korpus jedné strany → Tok s odsazením |
| `Pole.naplnit_slovnik()` | Slovník je společný a plní se z OBOU stran dřív, než se staví |
| `Pole.postavit_stranu()` | okno + sítko + Strana; hlídá filtrování vzduchu |
| `Pole.fakta()` | faktová strana; sáhnutí staví, pokud je potřeba |
| `Pole.dotazy()` | dotazová strana |
| `Pole.strana()` | strana podle klíče 'f' / 'q' |
| `Pole.ziskat_slovnik()` | společný slovník obou stran |
| `Pole.nastavit_polomery()` | obě r naráz; smějí se lišit |
| `Pole.ziskat_klic_mapovani()` | q<rq>f<rf> — store na dvojici poloměrů |
| `Pole.nacist_mapovani()` | dvojice pro současné poloměry |
| `Pole.ulozit_mapovani()` | zápis dvojic pro současné poloměry |

## `core/flow.py`

*Krok 1 workflow: rozprostřít věty do pole.*

| metoda | role v procesu |
|---|---|
| **`class Radek`** | Jeden řádek pole. Prázdný slot nemá token. |
| `Radek.je_prazdny()` | řádek z odsazení nemá token |
| **`class Tok`** | Věty srovnané za sebou i s odsazením. |
| `Tok.rozprostrit()` | věty za sebe i s odsazením kolem každé |
| `Tok.odsadit_vetu()` | r prázdných řádků před větu a za ni |
| `Tok.vyrobit_prazdne()` | prázdné řádky odsazení |
| `Tok.vybrat_tokeny()` | Zrno textu: normalizovaně jde interpunkce stranou. |
| `Tok.radek()` | řádek podle indexu, nebo None mimo pole |
| `Tok.vypsat_stredy()` | Řádky, které jsou slovo — tedy možné středy vektoru. |
| `Tok.pocet_radku()` | délka toku i s odsazením |

## `core/health.py`

*Kontrola zdraví dat — aby se tiché vady ozvaly samy.*

| metoda | role v procesu |
|---|---|
| **`class Nalez`** | Jeden problém. `co` je krátký klíč pro strojové čtení, `proc` |
| **`class Zdravi`** |  |
| `Zdravi.zkontrolovat()` | všechny kontroly za sebou |
| `Zdravi.korpus_je()` | je korpus čitelný a neprázdný? |
| `Zdravi.rozbor_je_cerstvy()` | Syrový text novější než korpus = příprava neproběhla. |
| `Zdravi.agenti_probehli()` | Korpus bez jediné návěsky znamená, že se agenti nepustili — |
| `Zdravi.vertikaly_pokryvaji()` | Aktivace bez sloupce v poli není vidět — a co není vidět, to se |
| `Zdravi.zlata_sedi_na_korpus()` | Zlatá sada odkazuje na věty; když se korpus přestaví, musí ten |
| `Zdravi.styly_existuji()` | Odkaz ze stránky na soubor, který není. Přejmenování stylů to |
| `Zdravi._json()` | čtení JSON, None při chybě |
| `Zdravi._korpus()` | korpus faktů, nebo prázdno |
| `zkontrolovat()` | kontrola bez zakládání objektu |
| `main()` | spuštění z příkazové řádky; kód 1 při chybě |

## `core/ingest.py`

*Příjem textu: syrový článek → korpus. Stavební bloky, ne skript.*

| metoda | role v procesu |
|---|---|
| **`class Cistic`** | Syrový text článku → řádky, ze kterých má smysl dělat věty. |
| `Cistic.vycistit_radek()` | poznámky a mezery pryč, zkratky scelené |
| `Cistic.z_textu()` | text → řádky, ze kterých má smysl dělat věty |
| `Cistic.ze_souboru()` | totéž ze souboru |
| `Cistic.ze_slozky()` | Článek → jeho řádky. Klíč je jméno souboru bez přípony a slouží |
| **`class Token`** | Jeden token tak, jak ho pole potřebuje. `lemma` se do korpusu |
| `Token.do_slovniku()` | token do tvaru, jaký ukládá korpus |
| **`class Rozbor`** | Klient k vlastní instanci UDPipe. JEDINÝ v projektu. |
| `Rozbor.poslat()` | jedno volání UDPipe, CoNLL-U ven |
| `Rozbor.rozebrat()` | Text → věty tokenů. Text projde týmž scelením zkratek jako |
| `Rozbor.z_conllu()` | CoNLL-U → tokeny; první sloupec musí být číslo |
| `Rozbor.vety_slovniku()` | věty rovnou ve tvaru korpusu |
| `Rozbor.lemmata()` | Jen lemmata, pro pojmy z dialogu. „román je druh díla" má pravou |
| **`class Vypovedi`** | Próza, nebo položka seznamu? |
| `Vypovedi.je_proza()` | má věta slovesný kořen? |
| `Vypovedi.oznacit()` | Na KAŽDÝ token schválně: šablona se skládá ze sousedů, takže |
| **`class Prijem`** | Fasáda: složka se články → korpus vět. |
| `Prijem.nacist()` | složka článků → řádky |
| `Prijem.rozebrat()` | Věty po dávkách — jedno volání na celý článek je pro UDPipe moc |
| `Prijem.slozit()` | Články → jeden korpus. Původ věty se drží MIMO `acts`: kdyby se |

## `core/interfaces.py`

*Abstraktní metody — jediná místa, kde se smí lišit implementace.*

| metoda | role v procesu |
|---|---|
| **`class ZdrojAktivaci`** | Co token aktivuje. Dnes UDPipe, ale může to být jiný rozbor, ruční |
| `ZdrojAktivaci.vypsat_aktivace()` | Aktivace tokenu, odfiltrované a v KANONICKÉM pořadí. Pořadí je |
| `ZdrojAktivaci.je_interpunkce()` | Při normalizovaném zrnu tyhle tokeny do pole nejdou. |
| `ZdrojAktivaci.urcit_tvar()` | Klíč tvaru do slovníku, už podle zvoleného zrna. |
| **`class Uloziste`** | Odkud se čte a kam se píše. Dnes JSON soubory; u větších dat to může |
| `Uloziste.nacist_vertikaly()` | Sloupce pole: [{'a': 'NOUN', 'g': 'UPOS'}, …] |
| `Uloziste.nacist_korpus()` | Věty jedné strany; `strana` je 'facts' nebo 'query'. |
| `Uloziste.nacist_mapovani()` | Dvojice pro dvojici poloměrů, klíč tvaru q<rq>f<rf>. |
| `Uloziste.ulozit_mapovani()` | zápis dvojic pro jednu dvojici poloměrů |
| **`class SkladacVektoru`** | Jak se z okolí udělá vektor. Dnes 'offset:aktivace' jako řetězec; |
| `SkladacVektoru.popsat_slot()` | Co jeden slot přispěje do vektoru. |
| `SkladacVektoru.slozit_vektor()` | Poskládá příspěvky slotů dohromady. |
| `SkladacVektoru.spocitat_klic()` | Klíč pro slučování. Týž klíč = tentýž vzor. |
| `SkladacVektoru.vypsat_vektor()` | Vektor k zobrazení. |
| **`class Sitko`** | Co z kterého offsetu do vektoru projde. Zdroj říká, CO token |
| `Sitko.propustit()` | Aktivace, které z tohohle slotu smějí do vektoru. |
| `Sitko.je_cinne()` | Filtruje sítko vůbec něco? Podle toho se hlásí do stavu. |
| **`class Slucovac`** | Kdy jsou dva vektory tatáž šablona. Dnes přesná shoda klíče; jinou |
| `Slucovac.zacit_sadu()` | Nová sada šablon. Předpona 'f' pro fakta, 'q' pro dotazy — id |
| `Slucovac.zaradit()` | Vrátí id šablony, pod kterou vektor spadá; novou v případě |
| `Slucovac.vypsat_sablony()` | id → {'vec': …, 'tvary': set, 'radky': list} |

## `core/language.py`

*Jazykový profil — česká slova ven z podmínek, do JSON.*

| metoda | role v procesu |
|---|---|
| **`class Jazyk`** |  |
| `Jazyk.cesta()` | kde leží profil daného kódu |
| `Jazyk.nacist()` | Profil se veze s kódem, ne s daty: bez něj mluvnice nefunguje |
| `Jazyk.ze_slovniku()` | profil z JSON; klíče od podtržítka jsou vysvětlivky |
| `Jazyk.vypsat_dostupne()` | jaké profily jsou k dispozici |
| `Jazyk.je_tazaci()` | začíná věta tázacím slovem? |
| `Jazyk.pta_se_na_zarazeni()` | ptá se slovo na zařazení („co je X?“)? |
| `Jazyk.cislo_mesice()` | jméno měsíce → číslo |
| `Jazyk.uvozuje()` | uvozuje slovo rok („v roce“, „r.“)? |
| `Jazyk.na_co_se_pta()` | Druh místa, kde odpověď leží — nebo None, když to není otázka |
| `Jazyk.je_prazdne()` | neříká slovo o obsahu nic? |

## `core/lexicon.py`

*Krok 3 workflow: sdílený slovník tvarů.*

| metoda | role v procesu |
|---|---|
| **`class Polozka`** |  |
| `Polozka.pocet_vyskytu()` | kolikrát tvar v obou stranách je |
| `Polozka.je_v_obou()` | je tvar ve faktech i v dotazech? |
| `Polozka.vypsat_nejcastejsi_sadu()` | nejčastější sada aktivací tvaru |
| `Polozka.spocitat_jistotu()` | Kolik různých sad aktivací tvar má. Jedna = jistota. |
| **`class Slovnik`** |  |
| `Slovnik.naplnit_z_toku()` | tok jedné strany do společného slovníku |
| `Slovnik.zapsat_radek()` | jeden řádek toku do položky tvaru |
| `Slovnik.zalozit_nebo_najit()` | jeden tvar, jedna položka |
| `Slovnik.zapsat_sadu()` | kolik různých sad aktivací tvar má |
| `Slovnik.zapsat_sablonu()` | zpětný odkaz tvar → šablona |
| `Slovnik.najit()` | položka podle tvaru |
| `Slovnik.cislo()` | pořadové číslo tvaru — id ve vazbách |
| `Slovnik.vypsat_tvary_v_obou()` | tvary společné oběma stranám |
| `Slovnik.vypsat_nejiste()` | Tvary s víc sadami aktivací — u skládání se u nich hádá. |

## `core/log.py`

*Log. Dvě úrovně a obě mají jiný účel.*

| metoda | role v procesu |
|---|---|
| `_kde()` | Modul a metoda, odkud se loguje. Bere se ze zásobníku, ne z parametru |
| `_udaje()` | klíč=hodnota na konec řádku |
| **`class Log`** |  |
| `Log.otevrit()` | otevře soubor logu |
| `Log.zavrit()` | zavře soubor logu |
| `Log.nastavit_uroven()` | ticho / info / debug |
| `Log.ziskat_uroven()` | současná úroveň |
| `Log.zapnuty()` | píše se na téhle úrovni vůbec něco? |
| `Log._radek()` | jeden řádek na konzoli i do souboru |
| `Log.info()` | Že průchod probíhá a kudy. Lehké, pár řádků na průchod. |
| `Log.debug()` | Co, jak, ve které metodě a s jakým výsledkem. |
| `Log.krok()` | Ohraničí fázi průchodu a změří ji. Konec se hlásí i při výjimce, |
| `nastavit()` | Přenastaví společný log. Volá se jednou při startu. |

## `core/settings.py`

*Nastavení průchodu. Nastaví se jednou a platí — nevleče se každým voláním.*

| metoda | role v procesu |
|---|---|
| **`class Nastaveni`** |  |
| `Nastaveni.overit_polomer()` | poloměr musí být 0–8 |
| `Nastaveni.ziskat_polomer()` | r jedné strany |
| `Nastaveni.nastavit_polomer()` | setter; jen poznamená, že model zestaral |
| `Nastaveni.polomer_faktu` *(vlastnost)* | r faktové strany |
| `Nastaveni.polomer_dotazu` *(vlastnost)* | r dotazové strany |
| `Nastaveni._prepnout()` | přepínač; změna značí model za zastaralý |
| `Nastaveni.syrove` *(vlastnost)* | Zrno textu. Syrově = s interpunkcí a rozlišením velikosti písmen. |
| `Nastaveni.stred_uvnitr` *(vlastnost)* | Je střed součástí vlastního vektoru? Když ne, je vzor obálkou |
| `Nastaveni.stred_atributy` *(vlastnost)* | Co ze středu smí do vlastního vektoru. Prázdné = všechno. |
| `Nastaveni.typy` *(vlastnost)* | Významový typ. Vypnutý musí zmizet i z pole, ne jen z vektoru. |
| `Nastaveni.klic_mapovani()` | Mapování má vlastní store pro každou dvojici poloměrů: šablony |
| `Nastaveni.oznacit_cerstvym()` | model je přepočítaný |
| `Nastaveni.do_slovniku()` | nastavení do JSON pro prohlížeč |
| `Nastaveni.ze_slovniku()` | nastavení z JSON |

## `core/side.py`

*Krok 4 workflow: jedna strana pole — fakta nebo dotazy.*

| metoda | role v procesu |
|---|---|
| **`class Vazba`** | Dvojice (slovo, šablona) — tatáž tabulka, jakou drží kód: |
| **`class Strana`** |  |
| `Strana.postavit()` | středy → šablony → vazby |
| `Strana.zaradit_stred()` | jeden střed: okno → vektor → šablona → vazba |
| `Strana.slozit_vektor()` | sloty → vektor přes skládač |
| `Strana.aktivace_slotu()` | Prázdný slot i slot mimo pole nepřispějí ničím — skládač si |
| `Strana.pripsat_k_sablone()` | tvar a řádek pod šablonu |
| `Strana.sestavit_vazby()` | dvojice (tvar, šablona) → výskyty |
| `Strana.vypsat_sablony()` | všechny šablony strany |
| `Strana.pocet_sablon()` | kolik šablon strana má |
| `Strana.pocet_stredu()` | kolik slov je středem |
| `Strana.spocitat_pomer()` | Šablon na střed. Blíží-li se jedné, nesdílí vzor skoro nikdo. |
| `Strana.vypsat_vazby_sablony()` | Zpětný odkaz: které vazby na tuhle šablonu ukazují. |
| `Strana.spocitat_prazdne_sloty()` | kolik z okna je odsazení |

## `core/sieve.py`

*Které aktivace se z kterého offsetu do vektoru dostanou.*

| metoda | role v procesu |
|---|---|
| `jmeno_aktivace()` | `Polarity=Neg` → `Polarity`; `AUX` zůstane `AUX`. |
| `filtruje_stred()` | Zahodí sítko na offsetu 0 neznámou aktivaci? |
| **`class SitkoVse`** | Propouští všechno — chování pole, dokud se sítko nezavede. |
| `SitkoVse.propustit()` | propustí všechno |
| `SitkoVse.je_cinne()` | nikdy nefiltruje |
| **`class SitkoStredu`** | Sousedy propouští celé, střed jen ve jmenovaných atributech. |
| `SitkoStredu.je_cinne()` | je zadán aspoň jeden povolený atribut? |
| `SitkoStredu.propustit()` | sousedy celé, střed jen ve jmenovaných |
| `SitkoStredu.projde()` | sedí aktivace na povolené jméno, atribut nebo skupinu? |
| **`class SitkoStupnovane`** | Rozlišení klesá se vzdáleností od středu. |
| `SitkoStupnovane.je_cinne()` | filtruje aspoň jedno patro? |
| `SitkoStupnovane.povolene()` | co se smí na daném offsetu; nula je výjimka |
| `SitkoStupnovane.propustit()` | podle patra vzdálenosti |
| `SitkoStupnovane.projde()` | shoda proti povoleným daného patra |

## `core/sources.py`

*Výchozí implementace tří švů: zdroj aktivací, skládač vektoru, slučovač.*

| metoda | role v procesu |
|---|---|
| **`class ZdrojZTokenu`** | Aktivace jsou rovnou v tokenu, kanonické pořadí dávají sloupce pole. |
| `ZdrojZTokenu.sestavit_poradi()` | katalog vertikál → kanonické pořadí |
| `ZdrojZTokenu.vypsat_aktivace()` | aktivace tokenu i s hrubými vrstvami, seřazené |
| `ZdrojZTokenu.dopocitat_hrube()` | Hrubé vrstvy nad jemnými. Chybí-li zdroj, vrstva se nepřidá — |
| `ZdrojZTokenu.odfiltrovat_typy()` | Vypnutý významový typ musí zmizet i z pole, ne jen z vektoru — |
| `ZdrojZTokenu.seradit_kanonicky()` | Pořadí je významné: táž sada jinak seřazená by dala jinou |
| `ZdrojZTokenu.je_interpunkce()` | při normalizovaném zrnu do pole nejde |
| `ZdrojZTokenu.urcit_tvar()` | klíč tvaru do slovníku podle zrna |
| **`class SkladacRetezcem`** | Vektor jako seznam řetězců „offset:aktivace". |
| `SkladacRetezcem.popsat_slot()` | co jeden slot přispěje; prázdný dá ∅ |
| `SkladacRetezcem.slozit_vektor()` | příspěvky slotů za sebe |
| `SkladacRetezcem.spocitat_klic()` | klíč pro slučování — týž klíč, týž vzor |
| `SkladacRetezcem.vypsat_vektor()` | vektor k zobrazení |
| **`class SlucovacShodou`** | Dva vektory jsou tatáž šablona, právě když jsou znak po znaku stejné. |
| `SlucovacShodou.zacit_sadu()` | nová sada šablon s předponou strany |
| `SlucovacShodou.zaradit()` | id šablony; novou v případě potřeby založí |
| `SlucovacShodou.zalozit_sablonu()` | nová šablona s pořadovým id |
| `SlucovacShodou.vypsat_sablony()` | id → vektor, tvary, řádky |

## `core/storage.py`

*Výchozí úložiště: JSON soubory, podadresář na každou datovou strukturu.*

| metoda | role v procesu |
|---|---|
| **`class UlozisteSouboru`** |  |
| `UlozisteSouboru.cesta()` | cesta uvnitř datového kořene |
| `UlozisteSouboru.cesta_struktury()` | každý datový typ svou složku |
| `UlozisteSouboru.cesta_mapovani()` | soubor na dvojici poloměrů |
| `UlozisteSouboru.overit_klic()` | klíč mapování musí být q<0-8>f<0-8> |
| `UlozisteSouboru.precist()` | JSON, nebo náhrada při chybě |
| `UlozisteSouboru.zapsat()` | Přes dočasný soubor a přejmenování — kdyby to spadlo uprostřed, |
| `UlozisteSouboru.nacist_vertikaly()` | katalog sloupců pole |
| `UlozisteSouboru.nacist_korpus()` | věty jedné strany |
| `UlozisteSouboru._nacist_strukturu()` | Když struktura ještě není, vezme se výchozí sada — pracovní kopie |
| `UlozisteSouboru.ulozit_vertikaly()` | zápis katalogu |
| `UlozisteSouboru.ulozit_korpus()` | zápis vět jedné strany |
| `UlozisteSouboru._ulozit_strukturu()` | zápis i do paměti, ať se čte totéž |
| `UlozisteSouboru.nacist_mapovani()` | dvojice; chybí-li, výchozí sada |
| `UlozisteSouboru.ma_mapovani()` | je store vlastní, nebo se bere výchozí? |
| `UlozisteSouboru.ulozit_mapovani()` | zápis dvojic |
| `UlozisteSouboru.vypsat_mapovani()` | všechny store naráz |
| `UlozisteSouboru.vratit_vychozi()` | Zahodí pracovní kopie struktur. Mapování zůstane. |

## `core/tvrzeni.py`

*Úzká mluvnice tvrzení — znalost se zadává větou, ne tabulkou.*

| metoda | role v procesu |
|---|---|
| `sceli_zkratky()` | R.U.R. → RUR, s.r.o. → sro |
| **`class Tvrzeni`** | `levy` a `pravy` jsou LEMMATA — podle nich se pojmy potkávají. |
| `Tvrzeni.znak()` | ⊂ ∈ = ≠ podle druhu |
| `Tvrzeni.do_slovniku()` | tvrzení do JSON pro uložení |
| `Tvrzeni.ze_slovniku()` | tvrzení z uloženého |
| **`class Dotaz`** | Otázka položená česky, ne přes „?". `cim` je None u „co je X?" — tam |
| **`class Nejasnost`** | Mluvnice tvar rozpoznala, ale neví, jestli je to podtřída, nebo |
| `Nejasnost.otazka()` | otázka pro člověka: druh, nebo konkrétní věc? |
| `Nejasnost.rozhodni()` | rozhodnutá nejasnost → tvrzení |
| **`class Mluvnice`** | Věta → tvrzení. Lemmatizaci obstará předaná funkce (u nás UDPipe), |
| `Mluvnice.rozeber()` | Vrací Tvrzeni, Dotaz, Nejasnost, nebo None. Otázka se testuje |
| `Mluvnice._tvrzeni()` | Lemma jako klíč, napsaný tvar k zobrazení. |
| `Mluvnice._ocistit()` | Povrchový tvar bez značek — lemmatizace se sem nesahá. |
| `Mluvnice._prvni_slovo()` | první slovo věty malými písmeny |
| `Mluvnice._najit()` | První značka z profilu, která ve větě je. Prázdno, když žádná. |
| `Mluvnice._obsahuje()` | Hledá se v ODSAZENÉM řetězci, aby značka chytla i na kraji věty. |
| `Mluvnice._rozdel()` | Dělí se v témž odsazeném řetězci, ve kterém se hledalo. |
| `Mluvnice._dotaz()` | Česky položená otázka. Konvence je táž jako u „? X Y": poslední |
| `Mluvnice._pojem()` | kus věty → lemma jako klíč uzlu |
| **`class Znalost`** | Přijatá tvrzení a odvozování nad nimi. |
| `Znalost.prijmi()` | Vrací None při přijetí, jinak důvod odmítnutí. |
| `Znalost.tvar()` | Jak se pojem napsal, když o něm poprvé padlo slovo. |
| `Znalost.zna()` | Padlo o tomhle pojmu vůbec někdy slovo? Slouží k rozřezání |
| `Znalost.zastupce()` | Synonyma splývají v jeden uzel; tohle je jeho jméno. |
| `Znalost.predci()` | Všechno, čím pojem tranzitivně je. TOHLE je ta expanze. |
| `Znalost.potomci()` | Všechno, co tímhle pojmem JE — opačný směr než `predci`. |
| `Znalost.je()` | True / False / None, kde None znamená POCTIVĚ „nevím". |
| `Znalost.naplnit_ze_svazu()` | Svaz z Wikidat jako podklad. Hrany dostanou zdroj `wikidata`, |
| `Znalost.vycistit()` | Zapomene, co se přidalo dialogem, a vrátí se k holému podkladu. |
| `Znalost.uloz()` | tvrzení na disk |
| `Znalost.nacti()` | tvrzení z disku, znovu přes prijmi() |

## `core/window.py`

*Krok 2 workflow: určit, kam kolem středu vektor dopadá.*

| metoda | role v procesu |
|---|---|
| **`class Slot`** |  |
| `zapsat_offset()` | offset jako řetězec se znaménkem |
| **`class Okno`** | Okolí středu při daném poloměru. |
| `Okno.urcit_sloty()` | sloty i-r … i+r kolem středu |
| `Okno.offsety()` | offsety okna; nula podle nastavení |
| `Okno.pocet_slotu()` | kolik slotů okno má |
| `Okno.zasahuje()` | Vejde se offset do okna? Podle toho se v paletě šedne. |
