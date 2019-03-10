# app-icp12-gui

## 使い方

1. ICP12をPCに接続
1. githubからclone
1. make run
1. 「connect」を押す　※

※接続できなかった場合、screenコマンドがパーミッションで弾かれているおそれがある。以下のコマンドでdialoutグループにユーザを登録する。  
```bash
$ sudo gpasswd -a [user] dialout
```
