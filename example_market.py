
    def connect(self):
        user_id = os.getenv("FLATTRADE_USER_ID") or ask("Flattrade user ID")
        token = os.getenv("FLATTRADE_USER_TOKEN") or getpass.getpass("Session token: ").strip()
        if not token or token == "YOUR_USER_TOKEN" or user_id == "YOUR_USER_ID":
            raise ValueError("Enter a real user ID and session token.")
        response = self.api.set_session(userid=user_id, password="", usertoken=token)
        if isinstance(response, dict) and response.get("stat") == "Not_Ok":
            raise RuntimeError(response.get("emsg", "Session setup failed."))
        self.session_created = True
        # Validate with an authenticated request instead of assuming the setter's
        # return value confirms or rejects the credentials.
        response = self.api.get_limits()
        if not isinstance(response, dict) or response.get("stat") != "Ok":
            error = response.get("emsg", "No successful response.") if isinstance(response, dict) else "No response."
            raise RuntimeError(f"Session validation failed: {error}")
        print("API session verified.")

    def start_socket(self):
        if self.socket_started:
            print("WebSocket is already started. Use x to stop it before restarting.")
            return
        raw = ask("Subscriptions (comma-separated EXCHANGE|TOKEN)", "NSE|11630")
        subscriptions = list(dict.fromkeys(s.strip() for s in raw.split(",") if s.strip()))
        if not subscriptions or any(len(s.split("|")) != 2 or not all(s.split("|")) for s in subscriptions):
            raise ValueError("Use NSE|11630 or NSE|22,BSE|522032.")
        self.subscriptions = subscriptions
        self.socket_opened.clear()
        self.socket_started = True
        try:
            self.api.start_websocket(
                order_update_callback=self.on_order,
                subscribe_callback=self.on_quote,
                socket_open_callback=self.on_open,
                socket_close_callback=self.on_close,
            )
        except Exception:
            self.socket_started = False
            raise
        if not self.socket_opened.wait(timeout=10):
            print("Still waiting for the connection. Use x to stop it before retrying.")

    def stop_socket(self):
        if not self.socket_started:
            return
        close = getattr(self.api, "close_websocket", None)
        if not callable(close):
            raise RuntimeError("This SDK has no close_websocket method; restart the program to reset the socket.")
        close()
        self.socket_started = False
        self.socket_opened.clear()

    def history(self, today=False):
        exchange = ask("Exchange", "NSE").upper()
        token = ask("Token", "22")
        if today:
            start = datetime.now(IST).replace(hour=0, minute=0, second=0, microsecond=0)
            end = datetime.now(IST)
        else:
            fmt = "%d-%m-%Y %H:%M:%S"
            start = datetime.strptime(ask("Start (DD-MM-YYYY HH:MM:SS, IST)"), fmt).replace(tzinfo=IST)
            end = datetime.strptime(ask("End (DD-MM-YYYY HH:MM:SS, IST)"), fmt).replace(tzinfo=IST)
        if end <= start:
            raise ValueError("End time must be later than start time.")
        show(self.api.get_time_price_series(exchange=exchange, token=token,
             starttime=int(start.timestamp()), endtime=int(end.timestamp()), interval=1))

    def run(self):
        while True:
            print("\nf: find symbol | m: quotes | p: security info | v: historical minutes")
            print("t: today's minutes | d: daily data | o: option chain")
            print("s: start WebSocket | x: stop WebSocket | q: quit")
            command = input("Choose: ").strip().lower()
            try:
                if command == "q":
                    break
                elif command == "f":
                    show(self.api.searchscrip(exchange=ask("Exchange", "NSE").upper(), searchtext=ask("Symbol search")))
                elif command in ("m", "p"):
                    method = self.api.get_quotes if command == "m" else self.api.get_security_info
                    show(method(exchange=ask("Exchange", "NSE").upper(), token=ask("Token", "22")))
                elif command in ("v", "t"):
                    self.history(today=command == "t")
                elif command == "d":
                    show(self.api.get_daily_price_series(exchange=ask("Exchange", "NSE").upper(),
                         tradingsymbol=ask("Trading symbol", "RELIANCE-EQ"), startdate=0))
                elif command == "o":
                    exchange = ask("Exchange", "NFO").upper()
                    symbol = ask("Current trading symbol (use f to find it)")
                    strike = float(ask("Strike price"))
                    count = int(ask("Count", "2"))
                    if strike <= 0 or count <= 0:
                        raise ValueError("Strike price and count must be positive.")
                    chain = self.api.get_option_chain(exchange=exchange, tradingsymbol=symbol,
                                                     strikeprice=strike, count=count)
                    if isinstance(chain, dict) and chain.get("values"):
                        for contract in chain["values"]:
                            print("\n", contract.get("tsym", "Contract"))
                            show(self.api.get_quotes(exchange=contract["exch"], token=contract["token"]))
                    else:
                        show(chain)
                elif command == "s":
                    self.start_socket()
                elif command == "x":
                    self.stop_socket()
                else:
                    print("Choose one of the listed options.")
            except Exception as exc:
                LOG.error("Request failed: %s", exc)

    def cleanup(self):
        try:
            self.stop_socket()
        except Exception as exc:
            LOG.error("WebSocket shutdown failed: %s", exc)
        if self.session_created:
            try:
                self.api.logout()
            except Exception as exc:
                LOG.error("Logout failed: %s", exc)


def main():
    app = MarketApp()
    try:
        app.connect()
        app.run()
    except (KeyboardInterrupt, EOFError):
        print("\nClosing.")
    except Exception as exc:
        LOG.error("Startup failed: %s", exc)
    finally:
        app.cleanup()


if __name__ == "__main__":
    main()
