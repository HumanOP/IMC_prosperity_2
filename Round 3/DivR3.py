from typing import Dict, List
from datamodel import OrderDepth, TradingState, Order
import collections
from collections import defaultdict
import random
import math
import copy
import numpy as np

empty_dict = {'AMETHYSTS' : 0, 'STARFRUIT' : 0, 'ORCHIDS' : 0, 'CHOCOLATE': 0, 'STRAWBERRIES':0, 'ROSES':0, 'GIFT_BASKET':0}


def def_value():
    return copy.deepcopy(empty_dict)

INF = int(1e9)

class Trader:

    position = copy.deepcopy(empty_dict)
    POSITION_LIMIT = {'AMETHYSTS' : 20, 'STARFRUIT' : 20, "ORCHIDS":100, 'CHOCOLATE': 250, 'STRAWBERRIES':350, 'ROSES':60, 'GIFT_BASKET':60}
    volume_traded = copy.deepcopy(empty_dict)

    person_position = defaultdict(def_value)
    person_actvalof_position = defaultdict(def_value)

    cpnl = defaultdict(lambda : 0)
    STARFRUIT_cache = []
    STARFRUIT_dim = 3
    ORCHID_cache = []
    ORCHID_dim=1
    steps = 0
    SUNLIGHT=0
    HUMIDITY=0
    ORCHID_ask=0
    ORCHID_gap=1e9
    ORCHID_gapth=2
    cont_buy_basket_unfill = 0
    cont_sell_basket_unfill = 0
    basket_std = 85   # to be set

    def calc_next_price_STARFRUIT(self):
        # STARFRUIT cache stores price from 1 day ago, current day resp
        # by price, here we mean mid price

        coef = [0.30363089,0.28605589,0.38965095]
        intercept =104.51152519937295
        nxt_price = intercept
        for i, val in enumerate(self.STARFRUIT_cache):
            nxt_price += val * coef[i]

        return int(round(nxt_price))

    def calc_next_price_ORCHID(self):
        # STARFRUIT cache stores price from 1 day ago, current day resp
        # by price, here we mean mid price
        
        coef = [4.24068053e-05,4.78569494e-03,9.97675042e-01]
        intercept =2.238184299086697
        nxt_price = intercept
        nxt_price+=coef[0]*self.SUNLIGHT
        nxt_price+=coef[1]*self.HUMIDITY
        for i, val in enumerate(self.ORCHID_cache):
            nxt_price += val * coef[i+2]

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
    


    def compute_orders_AMETHYST(self, product, order_depth, acc_bid, acc_ask):
        orders: list[Order] = []

        osell = collections.OrderedDict(sorted(order_depth.sell_orders.items()))
        obuy = collections.OrderedDict(sorted(order_depth.buy_orders.items(), reverse=True))

        sell_vol, best_sell_pr = self.values_extract(osell)
        buy_vol, best_buy_pr = self.values_extract(obuy, 1)

        cpos = self.position[product]

        mx_with_buy = -1

        for ask, vol in osell.items():
            if ((ask < acc_bid) or ((self.position[product]<0) and (ask == acc_bid))) and cpos < self.POSITION_LIMIT['AMETHYSTS']:
                mx_with_buy = max(mx_with_buy, ask)
                order_for = min(-vol, self.POSITION_LIMIT['AMETHYSTS'] - cpos)
                cpos += order_for
                assert(order_for >= 0)
                orders.append(Order(product, ask, order_for))

        mprice_actual = (best_sell_pr + best_buy_pr)/2
        mprice_ours = (acc_bid+acc_ask)/2

        undercut_buy = best_buy_pr + 1
        undercut_sell = best_sell_pr - 1

        bid_pr = min(undercut_buy, acc_bid-1) # we will shift this by 1 to beat this price
        sell_pr = max(undercut_sell, acc_ask+1)

        if (cpos < self.POSITION_LIMIT['AMETHYSTS']) and (self.position[product] < 0):
            num = min(40, self.POSITION_LIMIT['AMETHYSTS'] - cpos)
            orders.append(Order(product, min(undercut_buy + 1, acc_bid-1), num))
            cpos += num

        if (cpos < self.POSITION_LIMIT['AMETHYSTS']) and (self.position[product] > 15):
            num = min(40, self.POSITION_LIMIT['AMETHYSTS'] - cpos)
            orders.append(Order(product, min(undercut_buy - 1, acc_bid-1), num))
            cpos += num

        if cpos < self.POSITION_LIMIT['AMETHYSTS']:
            num = min(40, self.POSITION_LIMIT['AMETHYSTS'] - cpos)
            orders.append(Order(product, bid_pr, num))
            cpos += num
        
        cpos = self.position[product]

        for bid, vol in obuy.items():
            if ((bid > acc_ask) or ((self.position[product]>0) and (bid == acc_ask))) and cpos > -self.POSITION_LIMIT['AMETHYSTS']:
                order_for = max(-vol, -self.POSITION_LIMIT['AMETHYSTS']-cpos)
                # order_for is a negative number denoting how much we will sell
                cpos += order_for
                assert(order_for <= 0)
                orders.append(Order(product, bid, order_for))

        if (cpos > -self.POSITION_LIMIT['AMETHYSTS']) and (self.position[product] > 0):
            num = max(-40, -self.POSITION_LIMIT['AMETHYSTS']-cpos)
            orders.append(Order(product, max(undercut_sell-1, acc_ask+1), num))
            cpos += num

        if (cpos > -self.POSITION_LIMIT['AMETHYSTS']) and (self.position[product] < -15):
            num = max(-40, -self.POSITION_LIMIT['AMETHYSTS']-cpos)
            orders.append(Order(product, max(undercut_sell+1, acc_ask+1), num))
            cpos += num

        if cpos > -self.POSITION_LIMIT['AMETHYSTS']:
            num = max(-40, -self.POSITION_LIMIT['AMETHYSTS']-cpos)
            orders.append(Order(product, sell_pr, num))
            cpos += num

        return orders


    def compute_orders_regression(self, product, order_depth, acc_bid, acc_ask, LIMIT):
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
    
    def compute_orders_ORCHID(self, product, order_depth, acc_bid, acc_ask):
        orders: list[Order] = []

        if(self.ORCHID_ask-acc_bid<=self.ORCHID_gap-self.ORCHID_gapth and self.POSITION_LIMIT[product]>self.position[product]):
            orders.append(Order(product, acc_bid-2, -(self.POSITION_LIMIT[product]-abs(self.position[product]))))
        return orders
    
    def compute_orders_basket(self, order_depth):

        orders = {'STRAWBERRIES' : [], 'CHOCOLATE': [], 'ROSES' : [], 'GIFT_BASKET' : []}
        prods = ['STRAWBERRIES', 'CHOCOLATE', 'ROSES', 'GIFT_BASKET']
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

        res_buy = mid_price['GIFT_BASKET'] - mid_price['STRAWBERRIES']*6 - mid_price['CHOCOLATE']*4 - mid_price['ROSES'] - 374
        res_sell = mid_price['GIFT_BASKET'] - mid_price['STRAWBERRIES']*6 - mid_price['CHOCOLATE']*4 - mid_price['ROSES'] - 374

        trade_at = self.basket_std*0.25     # to be set

        gb_pos = self.position['GIFT_BASKET']
        gb_neg = self.position['GIFT_BASKET']
        
        ch_pos = self.position['CHOCOLATE']
        ch_neg = self.position['CHOCOLATE']
        
        st_pos = self.position['STRAWBERRIES']
        st_neg = self.position['STRAWBERRIES']

        ros_pos = self.position['ROSES']
        ros_neg = self.position['ROSES']
        
        


        basket_buy_sig = 0
        basket_sell_sig = 0

        if self.position['GIFT_BASKET'] == self.POSITION_LIMIT['GIFT_BASKET']:
            self.cont_buy_basket_unfill = 0
        if self.position['GIFT_BASKET'] == -self.POSITION_LIMIT['GIFT_BASKET']:
            self.cont_sell_basket_unfill = 0

        do_bask = 0

        if res_sell > trade_at:
            vol = self.position['GIFT_BASKET'] + self.POSITION_LIMIT['GIFT_BASKET']
            self.cont_buy_basket_unfill = 0 # no need to buy rn
            assert(vol >= 0)
            if vol > 0:
                do_bask = 1
                basket_sell_sig = 1
                orders['GIFT_BASKET'].append(Order('GIFT_BASKET', worst_buy['GIFT_BASKET'], -vol)) 
                orders['ROSES'].append(Order('ROSES', worst_buy['ROSES'], -vol))
                self.cont_sell_basket_unfill += 2
                gb_neg -= vol
                ros_pos -= vol
        elif res_buy < -trade_at:
            vol = self.POSITION_LIMIT['GIFT_BASKET'] - self.position['GIFT_BASKET']
            self.cont_sell_basket_unfill = 0 # no need to sell rn
            assert(vol >= 0)
            if vol > 0:
                do_bask = 1
                basket_buy_sig = 1
                orders['GIFT_BASKET'].append(Order('GIFT_BASKET', worst_sell['GIFT_BASKET'], vol))
                orders['ROSES'].append(Order('ROSES', worst_sell['ROSES'], vol))
                
                self.cont_buy_basket_unfill += 2
                gb_pos += vol
                ros_neg += vol


        return orders
    

        
    def compute_orders(self, product, order_depth, acc_bid, acc_ask):

        if product == "AMETHYSTS":
            return self.compute_orders_AMETHYST(product, order_depth, acc_bid, acc_ask)
        if product == "STARFRUIT":
            return self.compute_orders_regression(product, order_depth, acc_bid, acc_ask, self.POSITION_LIMIT[product])
        if product == "ORCHIDS":
            return self.compute_orders_ORCHID(product, order_depth, acc_bid, acc_ask)
        
    def run(self, state: TradingState) -> Dict[str, List[Order]]:
        """
        Only method required. It takes all buy and sell orders for all symbols as an input,
        and outputs a list of orders to be sent
        """
        # Initialize the method output dict as an empty dict
        result = {'AMETHYSTS' : [], 'STARFRUIT' : [],'ORCHIDS':[], 'CHOCOLATE': [], 'STRAWBERRIES':[], 'ROSES':[], 'GIFT_BASKET':[]}

        # Iterate over all the keys (the available products) contained in the order dephts
        for key, val in state.position.items():
            self.position[key] = val
        print()
        for key, val in self.position.items():
            print(f'{key} position: {val}')

        assert abs(self.position.get('ROSES', 0)) <= self.POSITION_LIMIT['ROSES']

        timestamp = state.timestamp

        if len(self.STARFRUIT_cache) == self.STARFRUIT_dim:
            self.STARFRUIT_cache.pop(0)
        if len(self.ORCHID_cache) == self.ORCHID_dim:
            self.ORCHID_cache.pop(0)

        _, bs_STARFRUIT = self.values_extract(collections.OrderedDict(sorted(state.order_depths['STARFRUIT'].sell_orders.items())))
        _, bb_STARFRUIT = self.values_extract(collections.OrderedDict(sorted(state.order_depths['STARFRUIT'].buy_orders.items(), reverse=True)), 1)

        _, bs_ORCHID = self.values_extract(collections.OrderedDict(sorted(state.order_depths['ORCHIDS'].sell_orders.items())))
        _, bb_ORCHID = self.values_extract(collections.OrderedDict(sorted(state.order_depths['ORCHIDS'].buy_orders.items(), reverse=True)), 1)

        self.STARFRUIT_cache.append((bs_STARFRUIT+bb_STARFRUIT)/2)
        self.ORCHID_cache.append((bs_ORCHID+bb_ORCHID)/2)
   
        INF = 1e9
    
        STARFRUIT_lb = -INF
        STARFRUIT_ub = INF


        if len(self.STARFRUIT_cache) == self.STARFRUIT_dim:
            STARFRUIT_lb = self.calc_next_price_STARFRUIT()-1
            STARFRUIT_ub = self.calc_next_price_STARFRUIT()+1

        ORCHID_mid = INF

        if(len(self.ORCHID_cache)==self.ORCHID_dim):
            ORCHID_mid=self.calc_next_price_ORCHID()

        AMETHYST_lb = 10000
        AMETHYST_ub = 10000

        # CHANGE FROM HERE

        self.SUNLIGHT=state.observations.conversionObservations["ORCHIDS"].sunlight
        self.HUMIDITY=state.observations.conversionObservations["ORCHIDS"].humidity
        self.ORCHID_ask=state.observations.conversionObservations["ORCHIDS"].askPrice
        acc_bid = {'AMETHYSTS' : AMETHYST_lb, 'STARFRUIT' : STARFRUIT_lb,"ORCHIDS":ORCHID_mid} # we want to buy at slightly below
        acc_ask = {'AMETHYSTS' : AMETHYST_ub, 'STARFRUIT' : STARFRUIT_ub,"ORCHIDS":ORCHID_mid} # we want to sell at slightly above
        self.ORCHID_gap=abs(state.observations.conversionObservations["ORCHIDS"].importTariff)-state.observations.conversionObservations["ORCHIDS"].transportFees
        self.steps += 1

        for product in state.market_trades.keys():
            for trade in state.market_trades[product]:
                if trade.buyer == trade.seller:
                    continue
                self.person_position[trade.buyer][product] = 1.5
                self.person_position[trade.seller][product] = -1.5
                self.person_actvalof_position[trade.buyer][product] += trade.quantity
                self.person_actvalof_position[trade.seller][product] += -trade.quantity

        for product in ['AMETHYSTS', 'STARFRUIT','ORCHIDS']:
            print(state.order_depths.keys())
            order_depth: OrderDepth = state.order_depths[product]
            orders = self.compute_orders(product, order_depth, acc_bid[product], acc_ask[product])
            result[product] += orders
            
        orders = self.compute_orders_basket(state.order_depths)
        result['GIFT_BASKET'] += orders['GIFT_BASKET']
        result['STRAWBERRIES'] += orders['STRAWBERRIES']
        result['CHOCOLATE'] += orders['CHOCOLATE']
        result['ROSES'] += orders['ROSES']

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
        for product in state.order_depths.keys():
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
        print("End transmission")
        print(result,ORCHID_mid,self.ORCHID_ask,self.position["ORCHIDS"])
        traderData="SAMPLE"
        
        conversions=abs(self.position["ORCHIDS"])
        return result, conversions, traderData