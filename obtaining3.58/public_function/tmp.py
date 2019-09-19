def binary_search(alist, item):
    e = len(alist)
    s = 0
    while alist[(e+s)/2] != item:
        if alist[(e+s)/2] > item:
            e = (e-s)/2
        else:
            s = (s+e)/2
    print (e + s) / 2


binary_search([1, 3, 5, 7, 9, 10], 1)