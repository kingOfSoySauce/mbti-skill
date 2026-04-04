#!/usr/bin/env python3
"""Merge curated famous people data with stablecharacter scraped data."""

import json
import re
from pathlib import Path

TYPES = [
    "INTJ", "INTP", "ENTJ", "ENTP",
    "INFJ", "INFP", "ENFJ", "ENFP",
    "ISTJ", "ISFJ", "ESTJ", "ESFJ",
    "ISTP", "ISFP", "ESTP", "ESFP",
]

CURATED = [
    ("Elon Musk", "INTJ", "Tech", "CEO of Tesla and SpaceX."),
    ("Friedrich Nietzsche", "INTJ", "Philosophy", "German philosopher and cultural critic."),
    ("Greta Thunberg", "INTJ", "Activism", "Climate change activist."),
    ("Ludwig van Beethoven", "INTJ", "Music", "Revolutionary classical composer."),
    ("Isaac Newton", "INTJ", "Science", "Physicist and mathematician who formulated the laws of motion."),
    ("Nikola Tesla", "INTJ", "Science", "Inventor and electrical engineer."),
    ("Christopher Nolan", "INTJ", "Film/TV", "Film director known for Inception and The Dark Knight."),
    ("Mark Zuckerberg", "INTJ", "Tech", "Co-founder and CEO of Facebook/Meta."),
    ("Ruth Bader Ginsburg", "INTJ", "Law", "U.S. Supreme Court Justice and gender equality advocate."),
    ("Suga (BTS)", "INTJ", "Music", "Rapper and producer in K-pop group BTS."),
    ("Bill Gates", "INTP", "Tech", "Microsoft co-founder and philanthropist."),
    ("Albert Einstein", "INTP", "Science", "Theoretical physicist who developed the theory of relativity."),
    ("Marie Curie", "INTP", "Science", "Physicist and chemist, first woman to win a Nobel Prize."),
    ("Abraham Lincoln", "INTP", "Politics", "16th President of the United States."),
    ("Charles Darwin", "INTP", "Science", "Naturalist who developed the theory of evolution."),
    ("Tina Fey", "INTP", "Entertainment", "Comedian, writer, and actress."),
    ("Meryl Streep", "INTP", "Film/TV", "Acclaimed actress with record Oscar nominations."),
    ("Socrates", "INTP", "Philosophy", "Classical Greek philosopher credited as the founder of Western philosophy."),
    ("Rene Descartes", "INTP", "Philosophy", "French philosopher and mathematician (I think, therefore I am)."),
    ("Felix Kjellberg (PewDiePie)", "INTP", "YouTube/Internet", "YouTube creator known as PewDiePie."),
    ("Steve Jobs", "ENTJ", "Tech", "Co-founder of Apple and tech visionary."),
    ("Julius Caesar", "ENTJ", "History", "Roman general and dictator."),
    ("Franklin D. Roosevelt", "ENTJ", "Politics", "32nd U.S. President, led during the Great Depression and WWII."),
    ("Margaret Thatcher", "ENTJ", "Politics", "British Prime Minister known as the Iron Lady."),
    ("Napoleon Bonaparte", "ENTJ", "History", "French military and political leader."),
    ("Jack Welch", "ENTJ", "Business", "Former CEO of General Electric."),
    ("MrBeast (Jimmy Donaldson)", "ENTJ", "YouTube/Internet", "YouTuber known for expensive stunts and philanthropy."),
    ("Jenna Ortega", "ENTJ", "Film/TV", "Actress known for Wednesday series."),
    ("Benjamin Franklin", "ENTP", "History", "Founding Father, inventor, and diplomat."),
    ("Thomas Edison", "ENTP", "Science", "Inventor of the light bulb and phonograph."),
    ("Mark Twain", "ENTP", "Literature", "American author and humorist."),
    ("Iron Man (Tony Stark)", "ENTP", "Fictional", "Marvel superhero and genius inventor."),
    ("Conan O Brien", "ENTP", "Entertainment", "TV host and comedian."),
    ("Voltaire", "ENTP", "Philosophy", "French Enlightenment writer and philosopher."),
    ("The Joker (DC)", "ENTP", "Fictional", "DC Comics villain and agent of chaos."),
    ("Carl Jung", "INFJ", "Psychology", "Swiss psychiatrist who founded analytical psychology."),
    ("J.K. Rowling", "INFJ", "Literature", "Author of the Harry Potter book series."),
    ("Martin Luther King Jr.", "INFJ", "Activism", "Civil rights leader and Nobel Peace Prize laureate."),
    ("Nelson Mandela", "INFJ", "Politics", "Anti-apartheid revolutionary and President of South Africa."),
    ("Mother Teresa", "INFJ", "Activism", "Catholic nun and humanitarian."),
    ("Fyodor Dostoevsky", "INFJ", "Literature", "Russian novelist known for psychological works."),
    ("Leo Tolstoy", "INFJ", "Literature", "Russian author of War and Peace and Anna Karenina."),
    ("Osamu Dazai", "INFJ", "Literature", "Influential Japanese novelist."),
    ("Noam Chomsky", "INFJ", "Science", "Linguist, philosopher, and social critic."),
    ("Jon Snow (Game of Thrones)", "INFJ", "Fictional", "Character from Game of Thrones, driven by duty and honor."),
    ("William Shakespeare", "INFP", "Literature", "English playwright and poet."),
    ("Princess Diana", "INFP", "History", "British royal and humanitarian icon."),
    ("Johnny Depp", "INFP", "Film/TV", "Actor known for eccentric character roles."),
    ("Audrey Hepburn", "INFP", "Film/TV", "Classic Hollywood actress and UNICEF ambassador."),
    ("J.R.R. Tolkien", "INFP", "Literature", "Author of The Lord of the Rings."),
    ("Kurt Cobain", "INFP", "Music", "Lead singer of Nirvana."),
    ("Vincent van Gogh", "INFP", "Art", "Dutch post-impressionist painter."),
    ("Robert Pattinson", "INFP", "Film/TV", "Actor known for Twilight and The Batman."),
    ("Tim Burton", "INFP", "Film/TV", "Film director known for dark, gothic style."),
    ("Frodo Baggins (LotR)", "INFP", "Fictional", "Hobbit protagonist of The Lord of the Rings."),
    ("Oprah Winfrey", "ENFJ", "Entertainment", "Media mogul and talk show host."),
    ("Ben Affleck", "ENFJ", "Film/TV", "Actor and filmmaker."),
    ("Harry Styles", "ENFJ", "Music", "Former One Direction member turned solo artist."),
    ("Maya Angelou", "ENFJ", "Literature", "Poet, memoirist, and civil rights activist."),
    ("Jimin (BTS)", "ENFJ", "Music", "Lead vocalist and dancer of K-pop group BTS."),
    ("Pierce Brosnan", "ENFJ", "Film/TV", "Actor known for playing James Bond."),
    ("Emma Stone", "ENFJ", "Film/TV", "Academy Award-winning actress."),
    ("Robin Williams", "ENFP", "Entertainment", "Comedian and actor known for his improvisational skills."),
    ("Robert Downey Jr.", "ENFP", "Film/TV", "Actor known for playing Iron Man."),
    ("Walt Disney", "ENFP", "Entertainment", "Founder of The Walt Disney Company."),
    ("Dr. Seuss", "ENFP", "Literature", "Childrens book author and illustrator."),
    ("Will Smith", "ENFP", "Entertainment", "Actor and rapper."),
    ("Oscar Wilde", "ENFP", "Literature", "Irish poet and playwright."),
    ("Aldous Huxley", "ENFP", "Literature", "Author of Brave New World."),
    ("Spider-Man (Peter Parker)", "ENFP", "Fictional", "Marvel superhero known for wit and responsibility."),
    ("George Washington", "ISTJ", "Politics", "First President of the United States."),
    ("Angela Merkel", "ISTJ", "Politics", "Former Chancellor of Germany."),
    ("Warren Buffett", "ISTJ", "Business", "CEO of Berkshire Hathaway and legendary investor."),
    ("Denzel Washington", "ISTJ", "Film/TV", "Academy Award-winning actor."),
    ("Queen Elizabeth II", "ISTJ", "History", "Longest-reigning British monarch."),
    ("Jeff Bezos", "ISTJ", "Tech", "Founder of Amazon."),
    ("Sigmund Freud", "ISTJ", "Psychology", "Founder of psychoanalysis."),
    ("Dwight D. Eisenhower", "ISTJ", "Politics", "34th U.S. President and WWII Supreme Commander."),
    ("Beyonce", "ISFJ", "Music", "Singer, songwriter, and cultural icon."),
    ("Vin Diesel", "ISFJ", "Film/TV", "Actor known for the Fast and Furious franchise."),
    ("Kate Middleton", "ISFJ", "History", "Princess of Wales."),
    ("Anne Frank", "ISFJ", "History", "Jewish diarist who documented life in hiding during WWII."),
    ("Selena Gomez", "ISFJ", "Music", "Singer and actress."),
    ("Ed Sheeran", "ISFJ", "Music", "Singer-songwriter known for acoustic pop."),
    ("Rosa Parks", "ISFJ", "Activism", "Civil rights activist known for the Montgomery bus boycott."),
    ("Captain America (Steve Rogers)", "ISFJ", "Fictional", "Marvel superhero driven by duty and protection."),
    ("Gordon Ramsay", "ESTJ", "Entertainment", "Celebrity chef and TV personality."),
    ("Emma Watson", "ESTJ", "Film/TV", "Actress and UN Women Goodwill Ambassador."),
    ("Michelle Obama", "ESTJ", "Politics", "Former First Lady of the United States."),
    ("Henry Ford", "ESTJ", "Business", "Founder of Ford Motor Company."),
    ("Condoleezza Rice", "ESTJ", "Politics", "Former U.S. Secretary of State."),
    ("Judge Judy", "ESTJ", "Entertainment", "TV judge and former prosecutor."),
    ("Kelsey Grammer", "ESTJ", "Film/TV", "Actor known for Frasier."),
    ("Taylor Swift", "ESFJ", "Music", "Award-winning pop/country music artist."),
    ("Ariana Grande", "ESFJ", "Music", "Pop singer and actress."),
    ("Hugh Jackman", "ESFJ", "Film/TV", "Actor known for Wolverine and musical theater."),
    ("Jennifer Garner", "ESFJ", "Film/TV", "Actress and entrepreneur."),
    ("Elton John", "ESFJ", "Music", "Legendary singer-songwriter and pianist."),
    ("Bill Clinton", "ESFJ", "Politics", "42nd President of the United States."),
    ("Steve Harvey", "ESFJ", "Entertainment", "TV host and comedian."),
    ("Eminem", "ISTP", "Music", "Influential rapper and hip-hop artist."),
    ("Michael Jordan", "ISTP", "Sports", "Basketball legend and global sports icon."),
    ("Clint Eastwood", "ISTP", "Film/TV", "Actor and director known for westerns."),
    ("Bruce Lee", "ISTP", "Sports", "Martial artist and actor."),
    ("Tom Cruise", "ISTP", "Film/TV", "Actor known for action films and stunts."),
    ("Miyamoto Musashi", "ISTP", "History", "Japanese swordsman and author of The Book of Five Rings."),
    ("Wolverine (Logan)", "ISTP", "Fictional", "Marvel superhero known for fierce independence."),
    ("Lady Gaga", "ISFP", "Music", "Pop star and actress known for avant-garde style."),
    ("Billie Eilish", "ISFP", "Music", "Grammy-winning alternative pop artist."),
    ("Lana Del Rey", "ISFP", "Music", "Singer-songwriter known for melancholic pop."),
    ("Bob Dylan", "ISFP", "Music", "Singer-songwriter and Nobel Prize in Literature laureate."),
    ("David Bowie", "ISFP", "Music", "Singer-songwriter and cultural icon."),
    ("Marilyn Monroe", "ISFP", "Film/TV", "Iconic actress and cultural symbol."),
    ("Michael Jackson", "ISFP", "Music", "King of Pop."),
    ("Jungkook (BTS)", "ISFP", "Music", "Youngest member of K-pop group BTS."),
    ("Harry Potter", "ISFP", "Fictional", "Wizard protagonist of the Harry Potter series."),
    ("Donald Trump", "ESTP", "Politics", "45th and 47th U.S. President and business mogul."),
    ("Ernest Hemingway", "ESTP", "Literature", "American novelist and journalist."),
    ("Madonna", "ESTP", "Music", "Queen of Pop and cultural icon."),
    ("Jack Nicholson", "ESTP", "Film/TV", "Acclaimed actor with multiple Oscars."),
    ("Winston Churchill", "ESTP", "Politics", "British Prime Minister during WWII."),
    ("Serena Williams", "ESTP", "Sports", "Tennis champion with 23 Grand Slam titles."),
    ("Han Solo (Star Wars)", "ESTP", "Fictional", "Smuggler and hero of the Star Wars saga."),
    ("Cristiano Ronaldo", "ESFP", "Sports", "Portuguese football player and global sports icon."),
    ("Rihanna", "ESFP", "Music", "Singer and entrepreneur."),
    ("Leonardo DiCaprio", "ESFP", "Film/TV", "Academy Award-winning actor."),
    ("Jamie Oliver", "ESFP", "Entertainment", "Celebrity chef and restaurateur."),
    ("Will Ferrell", "ESFP", "Entertainment", "Comedian and actor."),
    ("Pikachu (Pokemon)", "ESFP", "Fictional", "Electric-type Pokemon and global pop culture icon."),
    ("Barack Obama", "ENTP", "Politics", "44th President of the United States."),
]


def main():
    data_path = Path(__file__).parent.parent / "references" / "famous_people.json"

    # Load scraped stablecharacter data
    sc_data = {}
    if data_path.exists():
        sc_data = json.loads(data_path.read_text(encoding="utf-8"))

    # Build merged data
    final = {t: [] for t in TYPES}
    seen = {t: set() for t in TYPES}

    # Add curated entries
    for name, mbti_type, domain, description in CURATED:
        key = name.strip().lower()
        if key not in seen[mbti_type]:
            seen[mbti_type].add(key)
            slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
            final[mbti_type].append({
                "name": name,
                "mbti_type": mbti_type,
                "domain": domain,
                "description": description,
                "source": "curated",
                "detail_url": f"https://www.stablecharacter.com/personality-database/{slug}",
            })

    # Merge scraped data
    for t in TYPES:
        for p in sc_data.get(t, []):
            key = p.get("name", "").strip().lower()
            if key and key not in seen[t]:
                seen[t].add(key)
                # Keep only useful fields
                entry = {
                    "name": p["name"],
                    "mbti_type": t,
                    "domain": p.get("domain", "Other"),
                    "description": p.get("description", ""),
                    "source": p.get("source", "stablecharacter.com"),
                    "detail_url": p.get("detail_url", ""),
                }
                final[t].append(entry)

    # Stats
    total = sum(len(v) for v in final.values())
    for t in TYPES:
        domains = sorted(set(p["domain"] for p in final[t]))
        print(f"  {t}: {len(final[t]):2d} people  domains: {domains}")
    print(f"\nTotal: {total}")

    # Write
    data_path.write_text(json.dumps(final, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Written to {data_path}")


if __name__ == "__main__":
    main()
