import difflib
import json
import cdifflib
import queue
from transliterate import translit


class Station:
    def __init__(self, name, line):
        self.name = name
        self.line = line
        self.transfers = []

    def get_full_name(self):
        return self.name + ' (' + self.line.name + ' ' + self.line.number + ')'

    def add_transfer(self, station):
        self.transfers.append(station)


class Line:
    def __init__(self, name, number, color, stations):
        self.name = name
        self.number = number
        self.color = color
        self.stations = []
        for station_name in stations:
            self.stations.append(Station(station_name, self))

    def get_full_name(self):
        return self.name + ' ' + self.number


class Metro:
    def __init__(self):
        self.lines = []
        with open('Metro/lines.json', 'r') as file:
            for line in json.load(file):
                self.lines.append(Line(line['name'], line['number'], line['color'], line['stations']))

        with open('Metro/transfers.json', 'r') as file:
            for (station, transfers) in json.load(file).items():
                for transfer in transfers:
                    self.get_station(station).add_transfer(self.get_station(transfer))

        for line in self.lines:
            for i in range(len(line.stations)):
                if i > 0:
                    line.stations[i].add_transfer(line.stations[i - 1])
                if i + 1 < len(line.stations):
                    line.stations[i].add_transfer(line.stations[i + 1])

    def get_station(self, name):
        for line in self.lines:
            for station in line.stations:
                if name == station.get_full_name():
                    return station
        return None

    def get_similar_station_names(self, name):
        all_names = []
        for line in self.lines:
            for station in line.stations:
                all_names.append(station.name.lower())
                all_names.append(translit(station.name.lower(), 'ru', reversed=True))

        similar_names = difflib.get_close_matches(name.lower(), list(set(all_names)))

        res_names = []
        for similar_name in similar_names:
            for line in self.lines:
                for station in line.stations:
                    if station.name.lower() == similar_name or \
                            translit(station.name.lower(), 'ru', reversed=True) == similar_name:
                        res_names.append(station.get_full_name())

        return res_names

    def plot_route(self, departure_name, destination_name):
        departure_station = self.get_station(departure_name)
        destination_station = self.get_station(destination_name)

        q = queue.Queue()
        q.put(destination_station)
        dist = {destination_station: 0}
        p = {destination_station: None}

        while not q.empty() > 0:
            cur_station = q.get()
            cur_dist = dist[cur_station]
            for transfer in cur_station.transfers:
                if transfer not in dist.keys() or cur_dist + 1 < dist[transfer]:
                    dist[transfer] = cur_dist + 1
                    p[transfer] = cur_station
                    q.put(transfer)

        assert(departure_station in dist.keys())

        cur_station = departure_station
        output = cur_station.line.name + ': ' + cur_station.name

        last = cur_station
        while cur_station is not None:
            if last.line != cur_station.line:
                output += ' ---> ' + last.name + '\n'
                output += 'Transfer to ' + cur_station.line.get_full_name() + '\n'
                output += cur_station.line.name + ': ' + cur_station.name
            last = cur_station
            cur_station = p[cur_station]

        return output
