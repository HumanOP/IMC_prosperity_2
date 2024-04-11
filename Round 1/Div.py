from typing import Dict, List
from datamodel import OrderDepth, TradingState, Order
import collections
from collections import defaultdict
import random
import math
import copy
import numpy as np

empty_dict = {'STARFRUIT' : 0}


def def_value():
    return copy.deepcopy(empty_dict)

INF = int(1e9)

class Trader:

    position = copy.deepcopy(empty_dict)
    POSITION_LIMIT = {'STARFRUIT' : 20}
    volume_traded = copy.deepcopy(empty_dict)

    person_position = defaultdict(def_value)
    person_actvalof_position = defaultdict(def_value)

    cpnl = defaultdict(lambda : 0)
    STARFRUIT_cache = []
    STARFRUIT_dim = 5
    steps = 0
    

    def calc_next_price_STARFRUIT(self):
        # STARFRUIT cache stores price from 1 day ago, current day resp
        # by price, here we mean mid price

        coef = [0.12980497, 0.16754852, 0.19158442, 0.1975718,  0.29852644]

        intercept = 75.69568016648554
        nxt_price = intercept
        for i, val in enumerate(self.STARFRUIT_cache):
            nxt_price += val * coef[i]

        return int(round(nxt_price))

    def values_extract(self, order_dict, buy=0):
        tot_vol = 0
        best_val = -1
        mxvol = -1

        for ask, vol in order_dict.items():
            if(buy==0):
                vol *= -1
            tot_vol += vol
            if tot_vol > mxvol:
                mxvol = vol
                best_val = ask
        
        return tot_vol, best_val

    def compute_orders_regression(self, product, order_depth, acc_bid, acc_ask, LIMIT):
        LIMIT = self.POSITION_LIMIT[product]
        orders: list[Order] = []

        osell = collections.OrderedDict(sorted(order_depth.sell_orders.items()))
        obuy = collections.OrderedDict(sorted(order_depth.buy_orders.items(), reverse=True))

        sell_vol, best_sell_pr = self.values_extract(osell)
        buy_vol, best_buy_pr = self.values_extract(obuy, 1)

        cpos = self.position[product]

        for ask, vol in osell.items():
            if ((ask <= acc_bid) or ((self.position[product]<0) and (ask == acc_bid+1))) and cpos < LIMIT:
                order_for = min(-vol, LIMIT - cpos)
                cpos += order_for
                assert(order_for >= 0)
                orders.append(Order(product, ask, order_for))

        undercut_buy = best_buy_pr + 1
        undercut_sell = best_sell_pr - 1

        bid_pr = min(undercut_buy, acc_bid) # we will shift this by 1 to beat this price
        sell_pr = max(undercut_sell, acc_ask)

        if cpos < LIMIT:
            num = LIMIT - cpos
            orders.append(Order(product, bid_pr, num))
            cpos += num
        
        cpos = self.position[product]
        

        for bid, vol in obuy.items():
            if ((bid >= acc_ask) or ((self.position[product]>0) and (bid+1 == acc_ask))) and cpos > -LIMIT:
                order_for = max(-vol, -LIMIT-cpos)
                # order_for is a negative number denoting how much we will sell
                cpos += order_for
                assert(order_for <= 0)
                orders.append(Order(product, bid, order_for))

        if cpos > -LIMIT:
            num = -LIMIT-cpos
            orders.append(Order(product, sell_pr, num))
            cpos += num

        return orders
        
    def run(self, state: TradingState) -> Dict[str, List[Order]]:
        """
        Only method required. It takes all buy and sell orders for all symbols as an input,
        and outputs a list of orders to be sent
        """
        # Initialize the method output dict as an empty dict
        print("Start transmission")
        result = {'STARFRUIT' : []}

        # Iterate over all the keys (the available products) contained in the order dephts
        for key, val in state.position.items():
            self.position[key] = val
        for key, val in self.position.items():
            print(f'{key} position: {val}')

        timestamp = state.timestamp

        if len(self.STARFRUIT_cache) == self.STARFRUIT_dim:
            self.STARFRUIT_cache.pop(0)

        _, bs_STARFRUIT = self.values_extract(collections.OrderedDict(sorted(state.order_depths['STARFRUIT'].sell_orders.items())))
        _, bb_STARFRUIT = self.values_extract(collections.OrderedDict(sorted(state.order_depths['STARFRUIT'].buy_orders.items(), reverse=True)), 1)

        self.STARFRUIT_cache.append((bs_STARFRUIT+bb_STARFRUIT)/2)

        INF = 1e9
    
        STARFRUIT_lb = -INF
        STARFRUIT_ub = INF

        if len(self.STARFRUIT_cache) == self.STARFRUIT_dim:
            STARFRUIT_lb = self.calc_next_price_STARFRUIT()-1
            STARFRUIT_ub = self.calc_next_price_STARFRUIT()+1

        # CHANGE FROM HERE

        acc_bid = {'STARFRUIT' : STARFRUIT_lb} # we want to buy at slightly below
        acc_ask = {'STARFRUIT' : STARFRUIT_ub} # we want to sell at slightly above

        self.steps += 1

        for product in state.market_trades.keys():
            for trade in state.market_trades[product]:
                if trade.buyer == trade.seller:
                    continue
                self.person_position[trade.buyer][product] = 1.5
                self.person_position[trade.seller][product] = -1.5
                self.person_actvalof_position[trade.buyer][product] += trade.quantity
                self.person_actvalof_position[trade.seller][product] += -trade.quantity

        for product in ['STARFRUIT']:
            order_depth: OrderDepth = state.order_depths[product]
            orders = self.compute_orders_regression(product, order_depth, acc_bid[product], acc_ask[product],20)
            result[product] += orders

        for product in state.own_trades.keys():
            for trade in state.own_trades[product]:
                if trade.timestamp != state.timestamp-100:
                    continue
                # print(f'We are trading {product}, {trade.buyer}, {trade.seller}, {trade.quantity}, {trade.price}')
                self.volume_traded[product] += abs(trade.quantity)
                if trade.buyer == "SUBMISSION":
                    self.cpnl[product] -= trade.quantity * trade.price
                else:
                    self.cpnl[product] += trade.quantity * trade.price

        totpnl = 0

        # for product in state.order_depths.keys():
        #     settled_pnl = 0
        #     best_sell = min(state.order_depths[product].sell_orders.keys())
        #     best_buy = max(state.order_depths[product].buy_orders.keys())

        #     if self.position[product] < 0:
        #         settled_pnl += self.position[product] * best_buy
        #     else:
        #         settled_pnl += self.position[product] * best_sell
        #     totpnl += settled_pnl + self.cpnl[product]
        #     print(f"For product {product}, {settled_pnl + self.cpnl[product]}, {(settled_pnl+self.cpnl[product])/(self.volume_traded[product]+1e-20)}")
        
        product = 'STARFRUIT'
        settled_pnl = 0
        best_sell = min(state.order_depths[product].sell_orders.keys())
        best_buy = max(state.order_depths[product].buy_orders.keys())

        if self.position[product] < 0:
            settled_pnl += self.position[product] * best_buy
        else:
            settled_pnl += self.position[product] * best_sell
        totpnl += settled_pnl + self.cpnl[product]
        print(f"For product {product}, {settled_pnl + self.cpnl[product]}, {(settled_pnl+self.cpnl[product])/(self.volume_traded[product]+1e-20)}")


        print(f"Timestamp {timestamp}, Total PNL ended up being {totpnl}")
        # print(f'Will trade {result}')
        print("End transmission")
        traderData="SAMPLE"
        conversions=1
                
        return result, conversions, traderData