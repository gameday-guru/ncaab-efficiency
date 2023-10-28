# ncaab-efficiency
The NCAAB efficiency model.

## `ncaab-efficiency`
Run the model:
`python run ncaab-efficiency/model.py`

## Starting a new season
1. In the script block of `ncaab-efficiency/model.py`, change `ncaab_efficiency.retrodate` to your desired date. This will be the date that the model will start retrodating from. The model will retrodate from this date until the current date and then resume with normal execution.

```python
if __name__ == "__main__":
    ncaab_efficiency.retrodate = datetime.strptime("2023 3 9", "%Y %m %d").timestamp() # change this.
    # ncaab_efficiency.model_hostname = "nccab-efficiency"
    ncaab_efficiency.retro_window = (2 * 60 * 60)
    ncaab_efficiency.start()
```
2. Clear your existing redis cache: `redis-cli FLUSHALL`
3. Restart your service according to your means of deployment.

**Note:** In general retrodating is safe insofar as you can rely upon your surrounding logic services to fetch data for a particular date. 
