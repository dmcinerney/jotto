import nltk
nltk.download('words')
from nltk.corpus import words
word_list = words.words()
import numpy as np
from getpass import getpass
from tqdm import tqdm

hidden_word = 'jokes'

def make_set_hashable(setobj):
    return tuple(sorted(list(setobj)))


five_letter_words = [word for word in word_list if len(word) == 5 and not word[0].isupper()]
no_repeat_five_letter_words = [word for word in five_letter_words if len(set(word)) == 5]
hidden_word_letter_set_to_word = {}
for word in no_repeat_five_letter_words:
    letter_set = set(word)
    if make_set_hashable(letter_set) not in hidden_word_letter_set_to_word.keys():
        hidden_word_letter_set_to_word[make_set_hashable(letter_set)] = []
    hidden_word_letter_set_to_word[make_set_hashable(letter_set)].append(word)
guess_letter_set_to_word = {}
for word in five_letter_words:
    letter_set = set(word)
    if make_set_hashable(letter_set) not in guess_letter_set_to_word.keys():
        guess_letter_set_to_word[make_set_hashable(letter_set)] = []
    guess_letter_set_to_word[make_set_hashable(letter_set)].append(word)


def get_score(hidden_word, guess):
    score = 0
    for letter in set(guess):
        if letter in set(hidden_word):
            score += 1
    return score

def get_entropy(distribution):
    return -np.dot(distribution, np.log(distribution))


def get_distribution(possible_letter_sets):
    scores = np.array([len(hidden_word_letter_set_to_word[make_set_hashable(letter_set)])**2
                       for letter_set in possible_letter_sets])
    return scores/scores.sum()


class Jotto:
    def __init__(self, automatic_answerer=True, allow_override_guess=False):
        self.answerer = JottoAnswerer(automatic=automatic_answerer)
        self.guesser = JottoGuesser(allow_override=allow_override_guess)

    def play(self):
        answer = -2
        while answer != -1:
            guess = self.guesser.guess()
            answer = self.answerer.answer(guess)
            self.guesser.update_with_answer(answer)


class JottoAnswerer:
    def __init__(self, automatic=True):
        self.automatic = automatic
        if self.automatic:
            self.hidden_word = ''
            while len(set(self.hidden_word)) != 5 and self.hidden_word not in no_repeat_five_letter_words:
                print('Hidden word must be 5 letters long with no repeating letters.')
                self.hidden_word = getpass('Hidden word: ')

    def answer(self, guess):
        if self.automatic:
            if self.hidden_word == guess:
                print('You got it!')
                return -1
            score = get_score(self.hidden_word, guess)
        else:
            score = int(input('Enter score: '))
            assert -2 < score < 6
        print('Score: '+str(score))
        return score


class JottoGuesser:
    def __init__(self, k=10, s=10, allow_override=False):
        self.guesses = []
        self.answers = []
        self.possible_guess_letter_sets = set(guess_letter_set_to_word.keys())
        self.possible_hidden_word_letter_sets = set(hidden_word_letter_set_to_word.keys())
        self.k = k
        self.s = s
        self.perfect_match_words = None
        self.allow_override = allow_override

    @property
    def active_letters(self):
        active_letters = set()
        for letter_set in self.possible_hidden_word_letter_sets:
            active_letters = active_letters.union(letter_set)
        return active_letters

    def calculate_reward(self, guess):
        entropy_sum = 0
        possible_hidden_word_letter_sets = sorted(
            list(self.possible_hidden_word_letter_sets),
            key=lambda x: -len(hidden_word_letter_set_to_word[make_set_hashable(x)]))[:self.k]
        for letter_set in possible_hidden_word_letter_sets:
            answer = get_score(letter_set, guess)
            is_possible = np.array([answer == get_score(letter_set, guess)
                                    for letter_set in possible_hidden_word_letter_sets])
            entropy_sum += get_entropy(get_distribution(np.array(possible_hidden_word_letter_sets)[is_possible]))
        return -entropy_sum

    def trim(self):
        guess, answer = self.guesses[-1], self.answers[-1]
        possible_hidden_word_letter_sets = list(self.possible_hidden_word_letter_sets)
        for letter_set in tqdm(possible_hidden_word_letter_sets, total=len(possible_hidden_word_letter_sets)):
            if answer != get_score(letter_set, guess):
                if make_set_hashable(letter_set) == make_set_hashable(set(hidden_word)):
                    import pdb; pdb.set_trace()
                if len(self.possible_guess_letter_sets) == 1:
                    import pdb; pdb.set_trace()
                self.possible_hidden_word_letter_sets.remove(make_set_hashable(letter_set))
        if len(self.possible_hidden_word_letter_sets) == 1:
            if self.perfect_match_words is None:
                for letter_set in self.possible_hidden_word_letter_sets:
                    self.perfect_match_words = set(hidden_word_letter_set_to_word[make_set_hashable(letter_set)])
            if answer == 5:
                self.perfect_match_words.remove(guess)
        active_letters = self.active_letters
        possible_guess_letter_sets = list(self.possible_guess_letter_sets)
        for letter_set in tqdm(possible_guess_letter_sets, total=len(possible_guess_letter_sets)):
            remove = True
            for letter in letter_set:
                if letter in active_letters:
                    remove = False
                    break
            if remove:
                self.possible_guess_letter_sets.remove(make_set_hashable(letter_set))
        # guess_set_hashable = make_set_hashable(set(guess))
        # if guess_set_hashable in self.possible_guess_letter_sets:
        #     self.possible_guess_letter_sets.remove(guess_set_hashable)


    def update_with_answer(self, answer):
        self.answers.append(answer)
        if answer == -1:
            print('YOU WON IN '+str(len(self.answers))+' TURNS! CONGRATS!!!!!')
        else:
            self.trim()
            print(self.active_letters)

    def guess(self):
        if len(self.possible_hidden_word_letter_sets) > 1:
            guess_letter_sets = list(self.possible_guess_letter_sets)
            rewards = np.array([self.calculate_reward(letter_set)
                                for letter_set in tqdm(guess_letter_sets, total=len(guess_letter_sets))])
            indices = np.argsort(-rewards)
            guesses = []
            for i in indices[:self.s]:
                temp_guesses = guess_letter_set_to_word[make_set_hashable(guess_letter_sets[i])]
                print(rewards[i])
                print(temp_guesses)
                guesses.extend(temp_guesses)
        else:
            import pdb; pdb.set_trace()
            guesses = list(self.perfect_match_words)
            print(guesses)
        if self.allow_override:
            guess = ''
            while len(guess) != 5:
                guess = input('Type guess from above list or override and pick your own: ')
        else:
            guess = guesses[0]
        self.guesses.append(guess)
        print(self.guesses[-1])
        return self.guesses[-1]


if __name__ == '__main__':
    jotto = Jotto(automatic_answerer=False, allow_override_guess=True)
    # jotto = Jotto(automatic_answerer=True, allow_override_guess=True)
    jotto.play()
