from typing import Dict, List
from datamodel import OrderDepth, TradingState, Order
import collections
from collections import defaultdict
import random
import math
import copy
import numpy as np

empty_dict = {'PEARLS' : 0, 'BANANAS' : 0, 'COCONUTS' : 0, 'PINA_COLADAS' : 0, 'BERRIES' : 0, 'DIVING_GEAR' : 0, 'DIP' : 0, 'BAGUETTE': 0, 'UKULELE' : 0, 'PICNIC_BASKET' : 0}


def def_value():
    return copy.deepcopy(empty_dict)

INF = int(1e9)

class Trader:

    position = copy.deepcopy(empty_dict)
    POSITION_LIMIT = {'PEARLS' : 20, 'BANANAS' : 20, 'COCONUTS' : 600, 'PINA_COLADAS' : 300, 'BERRIES' : 250, 'DIVING_GEAR' : 50, 'DIP' : 300, 'BAGUETTE': 150, 'UKULELE' : 70, 'PICNIC_BASKET' : 70}
    volume_traded = copy.deepcopy(empty_dict)

    cpnl = defaultdict(lambda : 0)

    cont_buy_basket_unfill = 0
    cont_sell_basket_unfill = 0
    

    basket_std = 117

    def compute_orders_basket(self, order_depth):

        orders = {'DIP' : [], 'BAGUETTE': [], 'UKULELE' : [], 'PICNIC_BASKET' : []}
        prods = ['DIP', 'BAGUETTE', 'UKULELE', 'PICNIC_BASKET']
        osell, obuy, best_sell, best_buy, worst_sell, worst_buy, mid_price, vol_buy, vol_sell = {}, {}, {}, {}, {}, {}, {}, {}, {}

        for p in prods:
            osell[p] = collections.OrderedDict(sorted(order_depth[p].sell_orders.items()))
            obuy[p] = collections.OrderedDict(sorted(order_depth[p].buy_orders.items(), reverse=True))

            best_sell[p] = next(iter(osell[p]))
            best_buy[p] = next(iter(obuy[p]))

            worst_sell[p] = next(reversed(osell[p]))
            worst_buy[p] = next(reversed(obuy[p]))

            mid_price[p] = (best_sell[p] + best_buy[p])/2
            vol_buy[p], vol_sell[p] = 0, 0
            for price, vol in obuy[p].items():
                vol_buy[p] += vol 
                if vol_buy[p] >= self.POSITION_LIMIT[p]/10:
                    break
            for price, vol in osell[p].items():
                vol_sell[p] += -vol 
                if vol_sell[p] >= self.POSITION_LIMIT[p]/10:
                    break

        res_buy = mid_price['PICNIC_BASKET'] - mid_price['DIP']*4 - mid_price['BAGUETTE']*2 - mid_price['UKULELE'] - 375
        res_sell = mid_price['PICNIC_BASKET'] - mid_price['DIP']*4 - mid_price['BAGUETTE']*2 - mid_price['UKULELE'] - 375

        trade_at = self.basket_std*0.5
        close_at = self.basket_std*(-1000)

        pb_pos = self.position['PICNIC_BASKET']
        pb_neg = self.position['PICNIC_BASKET']

        uku_pos = self.position['UKULELE']
        uku_neg = self.position['UKULELE']


        basket_buy_sig = 0
        basket_sell_sig = 0

        if self.position['PICNIC_BASKET'] == self.POSITION_LIMIT['PICNIC_BASKET']:
            self.cont_buy_basket_unfill = 0
        if self.position['PICNIC_BASKET'] == -self.POSITION_LIMIT['PICNIC_BASKET']:
            self.cont_sell_basket_unfill = 0

        do_bask = 0

        if res_sell > trade_at:
            vol = self.position['PICNIC_BASKET'] + self.POSITION_LIMIT['PICNIC_BASKET']
            self.cont_buy_basket_unfill = 0 # no need to buy rn
            assert(vol >= 0)
            if vol > 0:
                do_bask = 1
                basket_sell_sig = 1
                orders['PICNIC_BASKET'].append(Order('PICNIC_BASKET', worst_buy['PICNIC_BASKET'], -vol)) 
                self.cont_sell_basket_unfill += 2
                pb_neg -= vol
                #uku_pos += vol
        elif res_buy < -trade_at:
            vol = self.POSITION_LIMIT['PICNIC_BASKET'] - self.position['PICNIC_BASKET']
            self.cont_sell_basket_unfill = 0 # no need to sell rn
            assert(vol >= 0)
            if vol > 0:
                do_bask = 1
                basket_buy_sig = 1
                orders['PICNIC_BASKET'].append(Order('PICNIC_BASKET', worst_sell['PICNIC_BASKET'], vol))
                self.cont_buy_basket_unfill += 2
                pb_pos += vol

        if int(round(self.person_position['Olivia']['UKULELE'])) > 0:

            val_ord = self.POSITION_LIMIT['UKULELE'] - uku_pos
            if val_ord > 0:
                orders['UKULELE'].append(Order('UKULELE', worst_sell['UKULELE'], val_ord))
        if int(round(self.person_position['Olivia']['UKULELE'])) < 0:

            val_ord = -(self.POSITION_LIMIT['UKULELE'] + uku_neg)
            if val_ord < 0:
                orders['UKULELE'].append(Order('UKULELE', worst_buy['UKULELE'], val_ord))

        return orders
    
    def run(self, state: TradingState) -> Dict[str, List[Order]]:
        """
        Only method required. It takes all buy and sell orders for all symbols as an input,
        and outputs a list of orders to be sent
        """
        # Initialize the method output dict as an empty dict
        result = {'PEARLS' : [], 'BANANAS' : [], 'COCONUTS' : [], 'PINA_COLADAS' : [], 'DIVING_GEAR' : [], 'BERRIES' : [], 'DIP' : [], 'BAGUETTE' : [], 'UKULELE' : [], 'PICNIC_BASKET' : []}

        # Iterate over all the keys (the available products) contained in the order dephts
        for key, val in state.position.items():
            self.position[key] = val
        print()
        for key, val in self.position.items():
            print(f'{key} position: {val}')

        assert abs(self.position.get('UKULELE', 0)) <= self.POSITION_LIMIT['UKULELE']

        timestamp = state.timestamp

        orders = self.compute_orders_basket(state.order_depths)
        result['PICNIC_BASKET'] += orders['PICNIC_BASKET']
        result['DIP'] += orders['DIP']
        result['BAGUETTE'] += orders['BAGUETTE']
        result['UKULELE'] += orders['UKULELE']

        # print(f'Will trade {result}')
        print("End transmission")
                
        return result