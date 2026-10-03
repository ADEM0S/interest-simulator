from dataclasses import dataclass
import re
import argparse
import datetime

PATTERN = r"([0-9]*\/[0-9]*\/[0-9]*),\s*(-?[0-9]*)"
DATETIME_PATTERN = r"%d/%m/%Y"

def daily_i(i:float, date:datetime.datetime):
    days_in_year = 364 + (date.year % 4 == 0)
    return i / days_in_year


class Entry:
    def __init__(self, date:datetime.datetime, amount:float) -> None:
        self.date = date
        self.amount = amount

    @staticmethod
    def from_str(datestr:str, amountstr:str):
        return Entry(datetime.datetime.strptime(datestr, DATETIME_PATTERN), float(amountstr))

    def __str__(self) -> str:
        return f"Entry:\n- date: {self.date}\n- amount: {self.amount}"


@dataclass
class Lot:
    deposit_date: datetime.date
    amount: float
    fidelity_accrued: float = 0.0

    @property
    def maturity_date(self):        
        year = self.deposit_date.year
        month = self.deposit_date.month
        day = self.deposit_date.day
        return datetime.datetime(year, month, day)

    @staticmethod
    def from_str(datestr:str, amountstr:str):
        return Lot(datetime.datetime.strptime(datestr, DATETIME_PATTERN), float(amountstr))

    def __str__(self) -> str:
        return f"Lot:\n- date: {self.deposit_date}\n- amount: {self.amount}"
    


class Simulator:
    def __init__(self, b:float, f:float) -> None:
        self.b = b
        self.f = f

        self.balance = 0.0
        self.history:list[Entry] = []
        self.lot_stack:list[Lot] = []
        self.fidelity_interest = 0.0
        self.base_interest = 0.0

    def add(self, lot:Lot) -> None:
        if lot.amount >= 0:
            self.lot_stack.append(lot)
            self.balance += lot.amount
        else:
            while self.lot_stack and self.lot_stack[-1].amount <= lot.amount:
                lot.amount -= self.lot_stack[-1].amount
                self.lot_stack.pop()
            if self.lot_stack and self.lot_stack[-1].amount >= lot.amount:
                self.lot_stack[-1].amount -= lot.amount
            else:
                raise Exception("Lot stack can not be negative.")
            self.balance -= lot.amount

    def deposit_base_interest(self):
        self.balance += self.base_interest
        self.base_interest = 0.0

    def deposit_fidelity_interest(self):
        self.balance += self.fidelity_interest
        self.fidelity_interest = 0.0

    def update(self, date:datetime.datetime):
        db = daily_i(self.b, date)
        df = daily_i(self.f, date)
        
        self.base_interest += self.balance * db
        
        for lot in self.lot_stack:
            if date < lot.maturity_date:
                lot.fidelity_accrued += lot.amount * df
            if date >= lot.maturity_date:
                self.fidelity_interest += lot.fidelity_accrued
                lot.fidelity_accued = 0.0
        
        self.history.append({
            "date": date,
            "balance": round(self.balance, 2),
            "base_interest": round(self.base_interest, 6),
            "fidelity_interest": round(sum(l.fidelity_accrued for l in self.lot_stack), 6),
        })


def parse_history(filepath:str) -> list[Entry]: 
    hf_data = []
    try:
        with open(filepath, "r") as hf:
            print("[INFO]: Reading History File")
            fmt = hf.readline()[:-1]
            print(f"[INFO]: format: {fmt}")
            matches = re.finditer(PATTERN, hf.read())
            # objs = map(lambda tup: (datetime.datetime.strptime(tup[0], "%d/%m/%Y"), float(tup[1]), matches)) 
            # hf_data = list(objs)
            for match in matches:
                tup = match.groups()
                hf_data.append(Lot.from_str(*tup))

    except Exception as e:
        print("[ERROR] Error Reading History File")
        print(e)

    return sorted(hf_data, key=lambda lot: lot.deposit_date)


def simulate(hf_data:list[Lot], b:float, f:float, end_date:datetime.datetime) -> list[dict]:
    simulator = Simulator(b, f)

    # Starting from the first date,
    # iterate over the relevant dates and compute the totals
    # relevant dates are:
    # - Quarters: 1 Jan, 1 Apr, 1 Jul, 1, Oct
    #   - Adds fidelity interest of money that stagnated for 12 months
    #       and for which the end date is in the preceding quarter.
    # - 1 Jan:
    #   - Adds base interest computed over the duration of the year
    #   - I = amount x base_interest x (days_before_end_of_year / days_in_the_year)

    # Entry index
    lot_i = 0
    current_date = hf_data[0].deposit_date
    day_1 = datetime.timedelta(days=1)

    while current_date <= end_date:

        # Deposit interests
        if current_date.day == 1:
            if current_date.month == 1:
                simulator.deposit_base_interest()
            if current_date.month % 3 == 1:
                simulator.deposit_fidelity_interest()

        # Deposit from history
        while lot_i < len(hf_data) and hf_data[lot_i].deposit_date <= current_date:
            lot = hf_data[lot_i]
            simulator.add(lot)
            lot_i += 1

        simulator.update(current_date)
        current_date += day_1

    return simulator.history


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--history-file", "-hf", type=str)
    parser.add_argument("--base", "-b", type=float)
    parser.add_argument("--fidelity", "-f", type=float)
    parser.add_argument("--end-date", "-e", default=datetime.datetime.now(), type=datetime.datetime)    
    args = parser.parse_args()

    hf_data = parse_history(args.history_file)
    
    print("[INFO]: Parsed History")
    for d in hf_data:
        print(d)

    print("[INFO]: Starting Simulation")
    
    hist = simulate(hf_data, args.base, args.fidelity, args.end_date)

    print("[INFO]: Finished Simulation")
    

    import pickle
    with open("history.pickle", "wb") as out:
        pickle.dump(hist, out)

if __name__ == "__main__":
    main()
