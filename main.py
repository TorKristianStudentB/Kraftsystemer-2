from TorKode.MakeGridFromFile import Grid, MakeGrid, read_xlsx, FileName, FolderName


if __name__ == "__main__":
    df=read_xlsx(FolderName, FileName) #leser excelfilen
    grid=MakeGrid(df)                  #oppretter nettet